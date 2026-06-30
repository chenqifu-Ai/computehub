# SPEC-WS-001: WebSocket 集群通信层设计规范

**版本**: 1.0  
**状态**: 草稿  
**设计者**: 小智  
**批准者**: [待定]

---

## 1. 概述

### 1.1 动机

当前集群通信基于 HTTP 短连接 + 5s 轮询，存在以下问题：

- **高延迟**: Hall 消息延迟平均 2.5s（轮询间隔的一半）
- **带宽浪费**: >95% 的 poll 请求返回空响应
- **低效率**: 广播一条消息需要 O(N) 次 HTTP POST 建连
- **不可靠**: 无消息确认，丢消息无感知

### 1.2 目标

- 消息延迟从 5s 降至 **<50ms**
- 空轮询率从 95% 降至 **0%**
- 广播方式从 O(N) HTTP 降至 **O(1) WS FanOut**
- 保持旧 Worker 兼容（HTTP fallback）

### 1.3 架构图

```
┌─────────────────────────────────────────────────────┐
│                     Gateway                         │
│  ┌──────────┐   ┌───────────┐   ┌────────────────┐  │
│  │ HTTP API │   │ WSHub     │   │ NodeManager    │  │
│  │ (端点)   │   │ (FanOut)  │   │ (节点管理)     │  │
│  └──────────┘   └───────────┘   └────────────────┘  │
│                       │                             │
└───────────────────────┼─────────────────────────────┘
                        │ WS (text, JSON)
           ┌────────────┼────────────┐
           │            │            │
      ┌────▼───┐   ┌───▼────┐   ┌───▼────┐
      │ Worker │   │ Worker │   │ Worker │
      │  (WS)  │   │  (WS)  │   │ (HTTP) │  ← 旧兼容
      └────────┘   └────────┘   └────────┘
```

---

## 2. 数据结构定义

### 2.1 WebSocket 消息通用格式

所有 WS 消息使用 **同一个 JSON 外壳**，通过 `msg_type` 区分消息类型：

```go
// Package gateway — WebSocket 消息协议
// 每个消息的首层结构

// WSMessage WebSocket 消息通用外壳
type WSMessage struct {
    MsgType   string              `json:"msg_type"`        // 消息类型 (见 2.2)
    Seq       uint64              `json:"seq,omitempty"`   // 序列号
    Timestamp int64               `json:"ts"`              // Unix 毫秒时间戳
    TraceID   string              `json:"trace_id,omitempty"` // 追踪ID（Phase 4）
    SenderID  string              `json:"sender_id"`        // 发送方 nodeID
    Priority  int                 `json:"p,omitempty"`      // 0=CRIT, 1=NORM, 2=GOSSIP

    // 按 msg_type 使用的字段（一次只用一组）
    // --- 注册/心跳 ---
    NodeID     string   `json:"node_id,omitempty"`       // 注册时用
    Platform   string   `json:"platform,omitempty"`      // 注册时用
    SubTopics  []string `json:"sub_topics,omitempty"`    // 订阅话题列表
    Status     string   `json:"status,omitempty"`        // "ok" / "error"
    Error      string   `json:"error,omitempty"`

    // --- 数据消息 ---
    Topic    string          `json:"topic,omitempty"`     // 话题
    From     string          `json:"from,omitempty"`      // 发送者
    FromName string          `json:"from_name,omitempty"`
    To       string          `json:"to,omitempty"`        // "all" 或具体 nodeID
    Content  string          `json:"content,omitempty"`   // 消息正文

    // --- 广播/拓扑 ---
    Event   string          `json:"event,omitempty"`      // node_join / node_leave / ...
    Payload json.RawMessage `json:"payload,omitempty"`    // 事件载荷
}
```

### 2.2 MsgType 枚举

```go
// MsgType 消息类型常量
const (
    // 系统消息（连接生命周期）
    MsgTypeRegister   = "register"     // Worker → Gateway: 注册连接
    MsgTypeRegistered = "registered"   // Gateway → Worker: 注册成功
    MsgTypePing       = "ping"         // Gateway → Worker | Worker → Gateway: 心跳
    MsgTypePong       = "pong"         // 回复 ping
    MsgTypeSubscribe  = "subscribe"    // Worker → Gateway: 变更订阅话题
    MsgTypeSubscribed = "subscribed"   // Gateway → Worker: 订阅成功

    // 数据消息
    MsgTypeHall      = "hall"          // 大厅群聊消息
    MsgTypeArcNet    = "arc_net"       // ARC-NET 广播消息
    MsgTypeHeartbeat = "heartbeat"     // 心跳载荷

    // 保留
    MsgTypeP2P   = "p2p"              // Phase 3: 跨节点直连
    MsgTypeACK   = "ack"              // Phase 4: 消息确认
)
```

### 2.3 服务端结构体

```go
// WSClient 代表一个 WebSocket 客户端连接
type WSClient struct {
    NodeID   string          // Worker 节点 ID
    Platform string          // "linux/arm64", "windows/amd64"
    Conn     *websocket.Conn // WS 连接实例
    Topics   map[string]bool // 订阅的话题集合 {"general":true, "alerts":true}
    RegAt    time.Time       // 注册时间
    LastPing time.Time       // 最近一次 ping/pong 时间
    Seq      uint64          // 本地序列号
    UserData map[string]string // 预留扩展字段
}

// WSHub WebSocket 管理中心（Gateway 端单例）
type WSHub struct {
    mu      sync.RWMutex
    clients map[string]*WSClient // key: nodeID

    // 指标
    MessagesSent     int64
    MessagesReceived int64
    ConnectCount     int64
    DisconnectCount  int64
}
```

### 2.4 传输限制

| 参数 | 值 | 说明 |
|------|-----|------|
| 单帧最大 | 16KB | 超过分片发送 |
| 写超时 | 2s | SetWriteDeadline |
| 读超时 | 60s | PongWait 检测断线 |
| 重连退避 | 1s → 2s → 4s → 8s → 16s → 30s cap | 指数退避 |

---

## 3. 协议流程

### 3.1 连接生命周期

```
Worker                                Gateway
  │                                       │
  │  1. HTTP Upgrade: GET /api/v1/ws      │
  │ ──────────────────────────────────▶    │
  │                                       │  升级到 WS
  │ ◀──────────────────────────────────   │
  │                                       │
  │  2. register (第一条消息)              │
  │  {"msg_type":"register",              │
  │   "node_id":"worker-arm",             │
  │   "platform":"linux/arm64",           │
  │   "sub_topics":["general","alerts"]}  │
  │ ──────────────────────────────────▶    │
  │                                       │  验证 node_id
  │  3. registered (回复)                 │
  │  {"msg_type":"registered",            │
  │   "status":"ok",                      │
  │   "seq":0}                            │
  │ ◀──────────────────────────────────    │
  │                                       │
  │  4. 数据消息交换（双向）               │
  │ ◀═══════════════════════════▶         │
  │                                       │
  │  5. ping/pong (每 10s)                │
  │  {"msg_type":"ping"}                  │
  │  {"msg_type":"pong"}                  │
  │ ◀═══════════════════════════▶         │
  │                                       │
  │  6. 断开连接                          │
  │ ── websocket.CloseNormalClosure ──▶   │
  │                                       │  Unregister
```

### 3.2 Hall 消息流

```
Worker A                          Gateway                          Worker B
   │                                 │                                │
   │  1. hall 消息                   │                                │
   │  {"msg_type":"hall",           │                                │
   │   "topic":"general",           │                                │
   │   "from":"worker-a",           │                                │
   │   "from_name":"端智",         │                                │
   │   "to":"all",                  │                                │
   │   "content":"大家好"}          │                                │
   │ ─────────────────────────▶     │   2. 存储到 HallState           │
   │                                │   3. FanOut (订阅者)            │
   │                                │ {"msg_type":"hall", ...}        │
   │                                │ ───────────────────────────▶   │
   │                                │   4. ACK 回复                  │
   │  {"msg_type":"hall",           │                                │
   │   "status":"ok"}               │                                │
   │ ◀─────────────────────────     │                                │
```

### 3.3 ARC-NET 广播流

```
Gateway                           Worker A, B, C
   │                                    │
   │  1. 节点上线事件                   │
   │  FanOutAll({"msg_type":"arc_net",  │
   │            "event":"node_join",    │
   │            "payload":{...}})       │
   │ ───────────────────────────────▶   │
   │                                    │ 每个 Worker 更新本地拓扑
   │  2. 节点下线事件                   │
   │  FanOutAll({"msg_type":"arc_net",  │
   │            "event":"node_leave",   │
   │            "payload":{...}})       │
   │ ───────────────────────────────▶   │
```

### 3.4 断线重连流程

```
Worker                                Gateway
  │                                       │
  │  1. WS 连接断开                       │
  │     (网络超时/进程重启/Gateway重启)   │
  │                                       │  Unregister(nodeID)
  │                                       │
  │  2. 等待 backoff (1s)                 │
  │     ↓                                 │
  │  3. 重连失败                          │
  │     backoff ×= 2                      │
  │     ↓                                 │
  │  4. 等待 backoff (2s)                 │
  │     ↓                                 │
  │  5. 重连成功                          │
  │     register → registered             │
  │     backoff 重置为 1s                 │
  │                                       │  重新加入 clients map
  │  6. 继续正常通信                      │
```

---

## 4. API 端点

### 4.1 新增端点

| 端点 | 方法 | 说明 | 位置 |
|------|------|------|------|
| `/api/v1/ws` | GET (Upgrade) | WebSocket 升级 | `gateway.go` |

### 4.2 保留端点（向后兼容）

| 端点 | 方法 | 说明 | 移除时机 |
|------|------|------|---------|
| `/api/v1/hall/poll` | GET | HTTP 轮询（旧 Worker） | Phase 5 |
| `/api/v1/hall/post` | POST | HTTP 发消息（旧 Worker） | Phase 5 |
| `/api/v1/cluster/broadcast` | POST | HTTP 广播（旧 Worker） | Phase 5 |

### 4.3 弃用端点（改走 WS，但保留存根）

| 端点 | 说明 | 移除时机 |
|------|------|---------|
| `/api/v1/worker/arc_net` | 旧 ARC-NET 广播接收 | Phase 5 |
| `/api/v1/worker/think` | 保留（Hall 走 WS 后这个还用于直接任务） | 不删 |

---

## 5. 客户端行为规范

### 5.1 Worker 端 WS 连接生命周期

```
启动
  │
  ├─▶ 尝试 WS 连接
  │     ├─▶ 成功 → 注册 → 消息接收循环
  │     └─▶ 失败 → HTTP fallback + 定时重试
  │
  ├─▶ 消息接收循环
  │     ├─▶ ping → 回复 pong（不触发 Agent）
  │     ├─▶ hall 消息 → 触发 Agent（节流判断）
  │     ├─▶ arc_net → 更新本地拓扑（不触发 Agent）
  │     ├─▶ registered → 更新状态
  │     └─▶ 其他 → WARN 日志 + 忽略
  │
  └─▶ 断线
        ├─▶ 关闭 oldConn
        ├─▶ 等待 backoff
        └─▶ 回到「尝试 WS 连接」
```

### 5.2 断线检测标准

| 条件 | 判定 | 动作 |
|------|------|------|
| ReadMessage 返回 error | 断线 | 关闭连接，启动重连 |
| WriteMessage 返回 error | 断线 | 关闭连接，启动重连 |
| 60s 未收到 pong | 断线（如果发送过 ping） | 关闭连接，启动重连 |
| CloseNormalClosure (1000) | 正常关闭 | 不重连（如果进程退出） |
| CloseGoingAway (1001) | 节点重启 | 重连 |

### 5.3 连接并发规则

- 每 Worker **仅 1 条 WS 连接**
- Worker 端读写各一个 goroutine（readPump + writePump），不加锁不竞争
- 写操作使用 `wsConn.WriteJSON()`，由内部锁保护（gorilla 默认不支持并发写，一台 WSConn 串行写）
- Gateway FanOut 遍历 client 时 RLock，写每条连接独立处理

---

## 6. 向后兼容策略

### 6.1 HTTP ↔ WS 共存规则

```
Worker 启动
  │
  ├─▶ 检查 GatewayURL 是否支持 WS
  │     ├─▶ 是：WS 优先，HTTP 为 fallback
  │     └─▶ 否：仅 HTTP（日志 WARN "WS not available, fallback HTTP"）
  │
  ├─▶ Worker 发消息
  │     ├─▶ WS 在线：走 WS（无 HTTP 查询参数）
  │     └─▶ WS 离线：走 POST /api/v1/hall/post
  │
  └─▶ Worker 收消息
        ├─▶ WS 在线：通过 readPump
        └─▶ WS 离线：HTTP poll 兜底
```

### 6.2 Gateway 端广播规则

```
BroadcastNodeEvent(nodeID, event)
  │
  ├─▶ wsHub.OnlineCount() > 0
  │     ├─▶ 是：FanOutAll → WS（异步，不等待）
  │     └─▶ 否：HTTP fallback（旧兼容）
  │
  └─▶ 即使 WS 成功了，也可以记录日志
        "WS broadcast: N delivered, M total"
```

---

## 7. 测试要点

### 7.1 单元测试

| 测试 | 覆盖 | 方法 |
|------|------|------|
| WSHub Register/Unregister | 增删 client | `go test -run TestWSHub` |
| WSHub FanOut | 消息分发到正确 client | Mock WebSocket Conn |
| FanOut 话题过滤 | 只发给订阅者 | Mock 不同 Topics 组合 |
| 并发安全 | 多 goroutine 读写 | `-race` | 
| 序列化/反序列化 | WSMessage 编解码 | 反射式 JSON 比较 |

### 7.2 集成测试

| 测试 | 方法 |
|------|------|
| Worker WS 注册→接收消息 | 启动 Gateway + Mock Worker |
| 断线重连 | 断开 WS → 等待 → 验证重连 |
| HTTP ↔ WS 切换 | WS 断开后验证 HTTP poll 启动 |
| 多 Worker 广播 | 3 个 WS Worker，1 个 HTTP Worker，验证全收到 |

### 7.3 性能测试基线

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 单条消息延迟 (p50) | ~2500ms | **<50ms** |
| 单条消息延迟 (p99) | ~5000ms | **<200ms** |
| Gateway 内存 (10 Worker) | ~30MB | **<50MB** |
| Gateway CPU (10 Worker) | ~2% idle | **<5% with WS** |

---

## 8. 实施顺序

```
Step 1 — 定义数据结构                [无代码依赖]
  写 WSMessage, WSClient, WSHub 结构体
  写 MsgType 常量
  → 编译通过

Step 2 — Gateway WSHub 核心          [依赖 Step 1]
  实现 NewWSHub, Register, Unregister, FanOut
  实现 GetClient, OnlineCount, ListClients
  实现 HandleWSUpgrade (HTTP→WS upgrade handler)
  → 测试：单例创建、注册注销、fanout 计数

Step 3 — Gateway 集成                [依赖 Step 2]
  gateway.go 注入 wsHub
  注册 /api/v1/ws 路由
  修改 BroadcastNodeEvent 走 wsHub
  → 测试：广播走 WS + HTTP fallback

Step 4 — Worker WS 客户端            [依赖 Step 2-3]
  HallClient 新增 WS 字段
  实现 connectWS, registerOnWS
  实现 StartWSLoop (替代 StartPollLoop)
  实现 wsReadLoop
  → 测试：Worker WS 连上 Gateway

Step 5 — 兼容层改造                  [依赖 Step 3-4]
  Worker 发消息：WS 优先 → HTTP fallback
  Gateway 广播：WS 优先 → HTTP fallback
  Worker 删除 sendBroadcast 等 6 函数
  → 测试：混合集群 (WS + HTTP Worker)

Step 6 — 智能节流                    [依赖 Step 4]
  thinkAndReply 增加 @提及判断
  wsReadLoop 跳过 self-message
  → 测试：无 @ 时不调 LLM
```

---

## 9. 文件清单

```
新增:
  src/gateway/gateway_ws.go          (~180 行)  WSHub + 协议 + handler

修改:
  src/gateway/gateway.go              (+10 行)  wsHub 字段 + 路由
  src/gateway/gateway_arcnet.go       (-30 行)  BroadcastNodeEvent + 删 postToWorker
  src/workercmd/worker_hall_client.go (+50 行)  改造 WS/HTTP 双模
  src/workercmd/worker_agent.go       (-220 行) 删除 Worker 级别广播

外部依赖:
  go get github.com/gorilla/websocket  (v1.5.x)

合计:
  新增 ~180 行，净减 ~30 行
```

---

## 10. 附录

### A. 核心变量命名对照

| 旧名 | 新名 | 位置 |
|------|------|------|
| `HallClient.StartPollLoop()` | `HallClient.StartWSLoop()` | `worker_hall_client.go` |
| `HallClient.pollOnce()` | 删除，由 `wsReadLoop()` 替代 | `worker_hall_client.go` |
| `OpcGateway.handleBroadcast()` | 保留（HTTP fallback） | `gateway.go` |
| `OpcGateway.postToWorker()` | `postToWorkerHTTP()` | `gateway_arcnet.go` |
| `WSClient.sendBroadcast()` | 删除 | `worker_agent.go` |
| `WSClient.broadcastNode*()` | 删除 | `worker_agent.go` |

### B. 日志格式规范

```
📡 WS Hub: worker-arm 已连接 (共 5 个连接)
📡 WS Hub: worker-arm 已断开 (剩余 4 个连接)
📡 WS FanOut: topic=general, delivered=4, skipped=1
📡 WS Hub: worker-arm 订阅话题 ["general","alerts","worker-arm"]
⚠️ WS Hub: worker-arm 无可用 WS 连接, fallback HTTP
⚠️ HallClient:worker-arm WS 连接失败: dial tcp ... (重试 4s)...
```

### C. 错误码

| 场景 | Gateway 返回 | Worker 行为 |
|------|-------------|-----------|
| WS 连接超时 | N/A | HTTP fallback + 后台重试 |
| 注册时 nodeID 为空 | `{"status":"error","error":"node_id required"}` | 日志 ERROR, 10s 后重连 |
| 注册时 nodeID 重复 | 关闭旧连接，接受新连接 | 因竞争条件，日志 WARN |
| 消息发送超时 | 断开该 Worker 连接 | WS 断线重连 |
| Gateway 重启 | 所有 WS 断开 | 各 Worker 重连（错峰+指数退避） |

---

> 本规范定义了 Phase 1 全部数据结构和协议。如有修改，更新版本号并通知集群所有节点。