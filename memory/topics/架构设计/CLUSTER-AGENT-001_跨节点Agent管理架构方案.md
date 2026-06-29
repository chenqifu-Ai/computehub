# 🕸️ CLUSTER-AGENT-001: 跨节点 Agent 集群管理架构方案

> 制定时间：2026-06-20
> 制定人：端智
> 适用场景：集群内多个 OpenClaw AI Agent 的统一发现、通信、管理
> 工程依托：ComputeHub + OpenClaw 基础设施

---

## 1. 🎯 目标

将集群中分散的多个 OpenClaw AI Agent（端智、米智、ECS小智等），通过 ComputeHub 网络桥接为一个统一的 **Agent Mesh**，实现：

1. **跨节点 Agent 通信** — 端智找米智对话，不再走proot→agent笨重管道
2. **Agent 自动发现与管理** — 新节点上线自动注册，下线自动摘除
3. **批量管理** — 一条命令查询/指挥所有 Agent

---

## 2. 🏗️ 总体架构

### 2.1 角色定义

```
                  ┌─────────────────────────────────────────┐
                  │             Mesh Gateway                │
                  │  (ComputeHub Gateway 增强)              │
                  │  Registry / Router / Broadcaster        │
                  └─────┬──────────────┬──────────┬─────────┘
                        │              │          │
               ┌────────▼───┐  ┌───────▼───┐  ┌──▼────────┐
               │ Mesh Agent │  │Mesh Agent │  │Mesh Agent │
               │ (端智)      │  │ (ECS小智) │  │ (米智)     │
               │ 红米手机    │  │ ECS服务器 │  │ 小米平板  │
               └───────────┘  └───────────┘  └───────────┘
```

| 角色 | 基于 | 职责 | 端口 |
|------|------|------|------|
| **Mesh Gateway** | ComputeHub Gateway | 注册中心、消息路由器、广播器 | 8282 |
| **Mesh Agent** | ComputeHub Worker + OpenClaw | 连接本机 OpenClaw Agent，对外暴露统一接口 | 8383 |

### 2.2 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: 用户接口层                                       │
│  API / Dashboard / openclaw agent --mesh 命令              │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: 批量管理层                                       │
│  广播、组播、批量状态、分布式任务                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 消息路由层                                       │
│  点对点路由、消息队列、ACK/重试                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 注册发现层                                       │
│  Agent注册/心跳/摘除、能力声明、健康检查                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 传输层                                           │
│  WebSocket (实时) + HTTP (查询) + Worker Shell (降级)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 📡 核心机制

### 3.1 Agent 注册与发现

**流程：**

```
Worker 启动/启动后
    │
    ├── 1. 探测本机 OpenClaw Gateway (127.0.0.1:18789)
    │       ├── 端口可达? → OpenClaw 版本号
    │       └── 端口不可达? → agent_status=unavailable
    │
    ├── 2. 注册到 Mesh Gateway
    │       POST /api/v1/mesh/register
    │       {
    │         "node_id": "local-arm",
    │         "openclaw_version": "2026.3.13",
    │         "openclaw_available": true,
    │         "capabilities": ["text", "image"],
    │         "proot_available": true,    // 有proot容器可调用openclaw agent
    │         "agent_routes": ["proot", "rest"] // 可用的通信路径
    │       }
    │
    ├── 3. 周期性心跳 (每60s)
    │       POST /api/v1/mesh/heartbeat
    │       {
    │         "node_id": "local-arm",
    │         "openclaw_status": "online",
    │         "load": 0.2,
    │         "last_active": timestamp
    │       }
    │
    └── 4. Gateway 管理注册表
        - 30s无心跳 → status=warning
        - 120s无心跳 → status=offline, 自动摘除
        - 新注册 → 广播给其他 Agent
```

**Gateway 注册表结构（内存 + 序列化到文件）：**

```json
{
  "agents": {
    "local-arm": {
      "node_id": "local-arm",
      "platform": "linux/arm64",
      "openclaw_version": "2026.3.13",
      "openclaw_available": true,
      "status": "online",
      "capabilities": ["text", "image"],
      "agent_routes": ["proot", "rest"],
      "last_seen": "2026-06-20T08:30:00Z",
      "version": "1.3.40",
      "routes": {
        "proot": "proot-distro login ubuntu -- bash -c 'cd /root && openclaw agent ...'",
        "rest": "http://10.55.112.157:8383/api/v1/agent/chat"
      }
    },
    "ecs-p2ph": { ... },
    "windows-mobile": { ... }
  }
}
```

### 3.2 消息路由

**三种通信路径，按优先级选择：**

| 优先级 | 路径 | 延迟 | 条件 | 原理 |
|--------|------|------|------|------|
| 🥇 | **WS Push** | ~500ms | Worker在线 + WS连 | Gateway直接Push命令，Worker执行openclaw agent --message |
| 🥈 | **REST Proxy** | ~1s | Worker在线 | Gateway POST → Worker /api/v1/agent/proxy → openclaw agent |
| 🥉 | **Shell Task** | ~5-15s | 任何情况 | 降级为 ComputeHub Task 提交 shell 命令 |

**消息格式（WebSocket JSON）：**

```json
{
  "type": "mesh_message",
  "msg_id": "msg-xxxx",
  "from": "端智",
  "to": "米智",
  "content": "米智你好，帮我看下磁盘空间",
  "priority": 5,
  "timeout": 60,
  "response_required": true,
  "reply_to": "msg_id"  // 回复时携带
}
```

**路由流程（以端智→米智为例）：**

```
端智 → POST /api/v1/mesh/send { to: "米智", content: "..." }
  │
  ├── Mesh Gateway 查注册表 → 米智 online, 有 WS 连接
  │     └── WS Push 到米智 Worker
  │           └── 米智 Worker 接收
  │                 ├── [路径A] 有 proot? → proot-distro login ubuntu -- openclaw agent --message "..."
  │                 ├── [路径B] 有 REST? → curl http://127.0.0.1:8383/api/v1/agent/proxy
  │                 └── [路径C] 都不行?  → 返回错误
  │
  └── 米智 Agent 处理完毕
        └── 回复 → WS Push 回 Gateway → Gateway 返回给端智
```

### 3.3 批量管理

**3.3.1 广播消息**

```
POST /api/v1/mesh/broadcast
{
  "message": "所有Agent请注意，15分钟后系统维护",
  "filter": { "status": "online" },  // 可选：只发给在线节点
  "timeout": 30
}

响应:
{
  "msg_id": "broadcast-xxx",
  "sent_to": ["local-arm", "ecs-p2ph", "windows-mobile"],
  "results": {
    "local-arm": { "success": true, "reply": "已收到" },
    "ecs-p2ph": { "success": true, "reply": "收到" },
    "windows-mobile": { "success": false, "error": "timeout" }
  }
}
```

**3.3.2 批量状态查询**

```
GET /api/v1/mesh/status?fields=node_id,status,openclaw_version,load

响应:
[
  { "node_id": "local-arm", "status": "online", "version": "1.3.40", "load": 0.3 },
  { "node_id": "ecs-p2ph", "status": "thinking", "version": "1.3.40", "load": 0.7 },
  { "node_id": "windows-mobile", "status": "offline", "version": "1.3.39" }
]
```

**3.3.3 批量命令**

```
POST /api/v1/mesh/exec
{
  "command": "status",      // think / status / health / shell
  "args": {},
  "nodes": ["all"],          // "all" | ["node1","node2"] | filter对象
  "parallel": true
}
```

---

## 4. 🧩 组件实现细节

### 4.1 Mesh Gateway（ComputeHub Gateway 扩展）

**新增 Go 源码文件：**

| 文件 | 职责 |
|------|------|
| `src/gateway/mesh_registry.go` | 注册表管理（增删改查、心跳超时摘除） |
| `src/gateway/mesh_router.go` | 消息路由（寻址、路径选择、队列） |
| `src/gateway/mesh_broadcast.go` | 广播/组播引擎 |
| `src/gateway/mesh_ws.go` | 与 Worker 的 WebSocket Mesh 通道 |
| `src/gateway/mesh_handler.go` | REST API handlers |

**新增 API 端点：**

```
POST   /api/v1/mesh/register      — Agent 注册
POST   /api/v1/mesh/heartbeat     — Agent 心跳
GET    /api/v1/mesh/registry      — 查看所有 Agent
GET    /api/v1/mesh/status        — 批量状态查询
POST   /api/v1/mesh/send          — 点对点发送消息
POST   /api/v1/mesh/broadcast     — 广播消息
POST   /api/v1/mesh/exec          — 批量命令执行
POST   /api/v1/mesh/proxy         — 给指定 Agent 的 OpenClaw 转发消息
GET    /api/v1/mesh/:node/log     — 获取 Agent 日志
```

**数据结构（内存注册表）：**

```go
type AgentRegistry struct {
    mu      sync.RWMutex
    agents  map[string]*AgentInfo
    stopCh  chan struct{}
}

type AgentInfo struct {
    NodeID            string    `json:"node_id"`
    Platform          string    `json:"platform"`
    OpenClawVersion   string    `json:"openclaw_version"`
    OpenClawAvailable bool      `json:"openclaw_available"`
    Status            string    `json:"status"`       // online, thinking, offline, warning
    Capabilities      []string  `json:"capabilities"`
    AgentRoutes       []string  `json:"agent_routes"`
    LastSeen          time.Time `json:"last_seen"`
    Version           string    `json:"version"`
    Load              float64   `json:"load"`
    WSConnected       bool      `json:"ws_connected"` // 是否有活跃 WS 通道
}
```

### 4.2 Mesh Agent（Worker 扩展）

Worker 侧新增 `mesh/` 子模块：

| 文件 | 职责 |
|------|------|
| `src/worker/mesh_client.go` | 连接 Gateway Mesh 通道，注册/心跳 |
| `src/worker/mesh_handler.go` | 处理接收到的 Mesh 消息 |
| `src/worker/openclaw_bridge.go` | 与本地 OpenClaw Agent 通信的桥梁 |

**OpenClaw 桥接层——三种模式：**

```
openclaw_bridge.go

┌────────────────────────────────────────────┐
│  OpenClawBridge                            │
│                                            │
│  模式A: CLI (最快实现)                     │
│    exec("openclaw agent --message ...")    │
│    → 但需要 proot 容器                     │
│                                            │
│  模式B: REST (推荐)                        │
│    POST http://127.0.0.1:18789/api/...     │
│    → 直接与本地 OpenClaw Gateway 通信      │
│    → 需要 OpenClaw Gateway 暴露 REST API  │
│                                            │
│  模式C: WS Proxy                           │
│    Client → Gateway WS → Worker WS →       │
│    → 本地 OpenClaw WS                      │
│    → 最低延迟，端到端实时对话              │
└────────────────────────────────────────────┘
```

**模式选择策略：**

```go
func (b *OpenClawBridge) SendMessage(msg string) (string, error) {
    // 1. 尝试 REST (最快, 0.5-2s)
    if b.restAvailable {
        return b.sendViaREST(msg)
    }
    // 2. 降级 CLI (2-10s, 需要 proot)
    if b.prootAvailable {
        return b.sendViaCLI(msg)
    }
    // 3. 降级 Worker Shell (5-15s, 通用)
    return "", fmt.Errorf("no OpenClaw bridge available on node %s", b.nodeID)
}
```

### 4.3 注册流程完整序列

```
Worker 启动
  │
  ├─ 1. 探测本地 OpenClaw
  │     GET http://127.0.0.1:18789/health → 200? 记录可用
  │     (已在 v1.3.40 的 port-probe 功能中实现)
  │
  ├─ 2. 建立 Mesh WS 连接到 Gateway
  │     ws://gateway:8282/api/v1/mesh/ws?node_id=local-arm
  │
  ├─ 3. 发送注册消息 (WS JSON)
  │     { "type": "register", "payload": { ... } }
  │
  ├─ 4. Gateway 确认
  │     { "type": "register_ack", "payload": { "agent_id": "local-arm" } }
  │
  ├─ 5. 心跳 (每 60s)
  │     { "type": "heartbeat", "payload": { "status": "online", "load": 0.1 } }
  │
  └─ 6. Gateway 广播新 Agent 上线给所有在线 Agent
        { "type": "agent_online", "payload": { "node_id": "local-arm", ... } }
```

---

## 5. 📋 API 接口规范

### 5.1 Mesh 消息格式（WS 与 HTTP 统一）

```go
type MeshMessage struct {
    Type      string          `json:"type"`      // register|heartbeat|message|reply|broadcast|exec|system
    MsgID     string          `json:"msg_id"`
    From      string          `json:"from"`
    To        string          `json:"to"`         // node_id | "broadcast" | "group:name"
    Content   string          `json:"content"`  
    Priority  int             `json:"priority"`   // 1-10
    Timeout   int             `json:"timeout"`    // seconds
    ReplyTo   string          `json:"reply_to,omitempty"`
    Metadata  json.RawMessage `json:"metadata,omitempty"`
}
```

### 5.2 回复格式

```json
{
  "type": "reply",
  "msg_id": "msg-xxxx",
  "reply_to": "msg-yyyy",
  "from": "米智",
  "to": "端智",
  "content": "磁盘剩余 32GB / 128GB，一切正常",
  "metadata": {
    "status": "completed",
    "latency_ms": 3420,
    "bridge_mode": "rest"
  }
}
```

---

## 6. 📅 实现计划（四阶段）

### Phase 1: 基础注册 + 心跳 + 状态查询（预估 3-5 天）

**做什么：**
- [ ] `mesh_registry.go` — 注册表数据结构 + 增删改查
- [ ] `mesh_handler.go` — REST API: register / heartbeat / registry / status
- [ ] GameWorker 扩展 — `mesh_client.go` 启动时注册 + 心跳
- [ ] OpenClaw 探测 — 复用 v1.3.40 port-probe 逻辑
- [ ] Gateway REST `/api/v1/mesh/registry` + `/status`

**交付物：**
- `curl http://gateway:8282/api/v1/mesh/status` 能看到所有节点 Agent 状态
- Worker 启动自动注册，断线自动摘除
- 状态持久化到文件（Gateway 重启恢复）

### Phase 2: 消息路由 + 点对点对话（预估 5-7 天）

**做什么：**
- [ ] `mesh_router.go` — 消息寻址 + 路径选择 + WS Push
- [ ] `mesh_ws.go` — Worker ↔ Gateway Mesh WS 通道
- [ ] `openclaw_bridge.go` — REST 模式（调用本地 OpenClaw Gateway）
- [ ] `mesh_handler.go` — POST /api/v1/mesh/send
- [ ] 如果本地 OpenClaw Gateway 没有 REST API → 实现一个简单的 /agent/chat proxy

**交付物：**
- 端智 → POST /mesh/send → 米智 → 回复 → 端智
- 延迟 1-5s（取决于 bridge 模式）

### Phase 3: 批量管理 + 广播（预估 3-5 天）

**做什么：**
- [ ] `mesh_broadcast.go` — 广播/组播 + 结果聚合
- [ ] `mesh_handler.go` — POST /broadcast, POST /exec
- [ ] Dashboard 页面 — `/mesh` 显示所有 Agent 状态
- [ ] 批量命令结果回传

**交付物：**
- 一条命令查询所有 Agent 状态
- 广播通知到所有 Agent
- Web 控制台管理 Agent

### Phase 4: Agent-to-Agent Mesh + 优化（预估 3-5 天）

**做什么：**
- [ ] 端智 ↔ 米智 双向实时对话（WS 全双工）
- [ ] Agent 在线状态推送（上线/下线/thinking 事件）
- [ ] 任务分配（"米智，处理这个 Windows 节点"）
- [ ] 降级策略自动选择（WS → REST → Shell）
- [ ] 性能优化 + 稳定性

**交付物：**
- Agent 之间可自由对话
- 自动路径切换（WS 断 → REST 降级 → 恢复后升回）
- 完整的集群 AI Agent 管理体验

---

## 7. ⚠️ 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| OpenClaw Gateway 无 REST API | 高 | Phase 2 阻塞 | 降级用 CLI/proot 模式（已实现）；后续为 OpenClaw Gateway 加 REST endpoint |
| Worker WS 需要保持长连接 | 中 | 资源占用 | 心跳间隔 60s，空闲 5min 可断开降级 HTTP |
| 消息丢失 | 低 | 对话质量 | msg_id + ACK + 重试（默认 3 次） |
| Agent 回复超时 | 中 | 用户体验 | 可配置超时（默认 30s），超时返回 partial 结果 |
| 大规模集群（>20 节点） | 低 | 性能 | 注册表内存存储足够，广播用 goroutine 并发 |

---

## 8. 🔗 与现有系统的关系

```
现有                新增
─────────────────────────────────────
ComputeHub Gateway  → + Mesh Gateway 扩展
ComputeHub Worker   → + Mesh Agent 扩展
OpenClaw Agent      →（不变，被 Mesh Agent 桥接）
proot→agent         → Phase 1-2 作为降级方案保留
COM-STD-001 ⑤       → 被 Phase 2 的 Mesh 路由取代
HEARTBEAT.md        → 数据源从手动填写改为 Mesh Status API
```

---

## 9. 💡 关键决策记录

1. **WS 还是 HTTP？** — 两者都支持。WS 用于实时对话，HTTP 用于状态查询。
2. **消息持久化？** — Phase 1-2 不需要，Phase 4 可选（存最近 100 条）。
3. **OpenClaw Gateway 改造？** — 不动 OpenClaw 源码。通过 Worker 代理存取。
4. **注册表放哪里？** — Gateway 内存 + 文件持久化（JSON 快照），不依赖数据库。
5. **Worker 的 WS 连接复用？** — 不再建新 WS，复用现有 Worker ↔ Gateway 的 WS 通道（新增 message type）。

---

## 10. 🚀 快速实验（Phase 0 — 今天可试）

在现有基础设施上，不做代码改动，验证 Mesh 通信的概念：

```bash
# 验证点：让 Gateway 通过 Worker Shell 转发消息到 OpenClaw

# 端智 → 米智
curl -s -X POST http://36.250.122.43:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "node_id":"local-arm",
    "command":"proot-distro login ubuntu -- bash -c \"cd /root && openclaw agent --agent main --message '"'"'米智你好，我是端智。帮我查一下现在几点钟了？'"'"' 2>&1 | tail -20\"",
    "timeout":120
  }'
```

验证通过后，Phase 1 就只需把这条调用封装成 REST API。