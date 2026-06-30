# SPEC-WS-TASK-001: WebSocket 实时任务分发

**版本**: v0.1-draft  
**日期**: 2026-06-13  
**状态**: Draft  
**作者**: 小智  
**关联文档**: [SPEC-WS-001](../SPEC-WS-001.md)

---

## 1. 背景

### 1.1 现状

当前 ComputeHub 的任务分发架构：

```
┌─────────┐   HTTP POST    ┌─────────┐   HTTP 轮询    ┌──────────┐
│  调度端  │ ──────────▶ │ Gateway  │ ◀──────────▶ │  Worker   │
│         │  /api/v1/tasks/submit      /api/v1/hall/poll    │ 节点      │
│         │              │           │              │           │
│         │              │   WS长连接  ───────────▶ │  群聊/广播 │
│         │              │                     (hall_message / arc_net)
└─────────┘              └─────────┘              └──────────┘
```

- 任务提交走 HTTP `/api/v1/tasks/submit`
- Worker 通过 HTTP `/api/v1/hall/poll` 轮询拉取任务
- WS 长连接目前仅用于群聊消息和 ARC-NET 广播，**不承载任务分发**

### 1.2 问题

| 问题 | 说明 |
|------|------|
| 延迟 | HTTP 轮询有固定间隔（默认 ~15s），实时性差 |
| 浪费 | 无任务时也要周期性轮询，浪费连接 |
| 无状态 | 轮询不保证消息顺序和可靠性 |
| 扩展性 | 轮询模型在高并发场景下 Gateway 负载大 |

### 1.3 目标

通过 WS 长连接实现**实时任务推送**，消除轮询延迟：

```
┌─────────┐   HTTP POST      ┌─────────┐
│  调度端  │ ──────────▶ │ Gateway  │
│         │  /api/v1/tasks/submit   │
│         │                      │
│         │                      │ WS: task_message 实时推送
└─────────┘                      │
                                 ▼
                          ┌──────────┐
                          │  Worker   │
                          │  实时接收  │
                          └──────────┘
```

---

## 2. 架构设计

### 2.1 消息格式

#### 2.1.1 任务分发消息 (task_message)

```jsonc
{
  "msg_type": "task_message",          // 新增消息类型
  "task_id": "task-xxx-xxxxx",         // 任务ID（唯一）
  "node_id": "worker-arm",             // 目标节点
  "command": "uname -a",               // 要执行的命令
  "timeout": 30,                       // 超时秒数
  "priority": 5,                       // 优先级 1-10
  "source_type": "api",                // 来源: api/direct/scheduled
  "seq": 1001,                         // 序列号（保序）
  "timestamp": 1718245678000           // 时间戳(ms)
}
```

#### 2.1.2 任务执行结果消息 (task_result)

Worker 执行完成后，通过 WS 回传结果：

```jsonc
{
  "msg_type": "task_result",           // 结果上报
  "task_id": "task-xxx-xxxxx",         // 关联任务ID
  "success": true,                     // 是否成功
  "exit_code": 0,                      // 退出码
  "stdout": "Linux ...\n",             // 标准输出
  "stderr": "",                        // 错误输出
  "duration": "104ms",                 // 执行耗时
  "seq": 1002                          // 序列号
}
```

### 2.2 消息流

```
调度端                    Gateway                      Worker (WS)
  │                        │                              │
  │── POST /tasks/submit ──▶│                              │
  │                        │                              │
  │                        │── WS: task_message ─────────▶│
  │                        │                              │
  │                        │                              │── 执行命令
  │                        │                              │
  │                        │◀─ WS: task_result ───────────│
  │                        │                              │
  │── GET /tasks/detail ──▶│── 查库返回结果 ◀─────────────│
```

### 2.3 关键设计决策

| 决策 | 方案 | 理由 |
|------|------|------|
| **推送 vs 轮询** | 推送为主，轮询兜底 | 实时性优先，断线时自动切轮询 |
| **消息可靠性** | seq 序列号 + ACK | 丢消息可检测可重推 |
| **任务超时** | Gateway 侧独立 timer | Worker 断线后仍可清理 |
| **并发控制** | Worker 侧 concurrent 限制 | 已有 `--concurrent` 参数 |
| **双向通信** | Worker 回传结果 via WS | 减少轮询查询，但保留 HTTP detail 接口兼容 |

---

## 3. 实施方案

### Phase 0: 基础准备（预计 2h）

**目标**: 确认现有代码基线，不改动任何东西

- [ ] 确认 WS 连接状态：各节点 WS 是否稳定在线
- [ ] 确认 Worker 任务执行链路完整可用
- [ ] 确认 `HallClient.wsReadLoop` 当前处理的消息类型
- [ ] 确认现有 task 表的存储结构（SQLite/内存）

### Phase 1: Gateway 侧推送（预计 4h）

**目标**: Gateway 收到任务后，通过 WS 推送给目标节点

**改动文件**: `src/gateway/gateway.go`

```go
// 新增函数：WS 推送任务
func (g *OpcGateway) pushTaskToWorker(taskID, nodeID, command string, timeout int, priority int) {
    // 1. 查节点 WS 连接
    client := g.wsHub.GetClient(nodeID)
    if client == nil {
        // WS 不在线，走 HTTP poll 兜底
        g.submitTaskToDB(taskID, nodeID, command, timeout, priority)
        return
    }
    
    // 2. 构建 WS 消息
    wsMsg := &WSMessage{
        MsgType:   "task_message",
        SenderID:  "gateway",
        Payload:   []byte(json 序列化),
        Timestamp: time.Now().UnixMilli(),
    }
    
    // 3. 通过 WS 推送
    g.wsHub.SendTo(nodeID, wsMsg)
    
    // 4. 注册结果回调：收到 task_result 后存库
    g.registerTaskCallback(taskID, nodeID)
}
```

**改动清单**:
- [ ] `gateway.go`: `pushTaskToWorker()` 新函数
- [ ] `gateway.go`: 修改 `handleTaskSubmit` — 收到任务后调用 `pushTaskToWorker`
- [ ] `gateway.go`: 新增任务结果 WS 消息处理回调
- [ ] `gateway_ws.go`: 确认 `SendTo` 支持非广播消息
- [ ] `gateway_ws.go`: 增加 `handleTaskResult` 处理 task_result 消息

### Phase 2: Worker 侧接收（预计 4h）

**目标**: Worker 收到 `task_message` 后执行并回传结果

**改动文件**: `src/workercmd/worker_hall_client.go`

```go
// 在 wsReadLoop 中增加 case
func (hc *HallClient) wsReadLoop() {
    for {
        // ... 现有代码 ...
        
        switch envelope.MsgType {
        // ... 现有 case ...
        
        case "task_message":
            // 解析任务参数
            taskID := envelope.TaskID
            command := envelope.Command
            timeout := envelope.Timeout
            
            // 执行命令
            stdout, stderr, exitCode, duration := hc.executeCommand(command, timeout)
            
            // 回传结果
            hc.wsMu.Lock()
            hc.wsConn.WriteJSON(WSMessage{
                MsgType:   "task_result",
                TaskID:    taskID,
                Success:   exitCode == 0,
                ExitCode:  exitCode,
                Stdout:    stdout,
                Stderr:    stderr,
                Duration:  duration.String(),
            })
            hc.wsMu.Unlock()
            
        // ...
        }
    }
}
```

**改动清单**:
- [ ] `worker_hall_client.go`: `wsReadLoop` 增加 `case "task_message"`
- [ ] `worker_hall_client.go`: `WSMessage` 增加 `TaskID`, `Command`, `Timeout` 字段
- [ ] `worker_hall_client.go`: 执行命令并回传 `task_result`
- [ ] `worker_hall_client.go`: 增加 `task_result` 消息发送方法

### Phase 3: 可靠性增强（预计 3h）

**目标**: 消息保序、重推、超时清理

**改动清单**:
- [ ] 新增 seq 序列号机制 — 每条消息带递增 seq
- [ ] Worker 侧 ACK 确认 — 收到任务后回传 `task_ack`
- [ ] Gateway 侧超时 timer — 任务提交后 x 秒无结果则重试/告警
- [ ] Worker 侧任务队列 — 并发控制（已有 `--concurrent` 参数复用）
- [ ] 断线重推 — Worker 断线重连后，Gateway 补推未完成的任务

### Phase 4: 兼容与回退（预计 2h）

**目标**: 新旧 Worker 共存，确保稳定性

**改动清单**:
- [ ] WS 推送失败自动切回 HTTP poll（已有机制复用）
- [ ] 兼容不升级的旧 Worker（WS 消息 type 未知时忽略）
- [ ] 升级时新旧 Worker 共存测试
- [ ] 监控指标：WS 推送成功率、任务延迟、消息丢失率

### Phase 5: 测试与优化（预计 3h）

- [ ] 单元测试：消息序列化/反序列化
- [ ] 集成测试：全平台节点 (Linux/Windows/Android)
- [ ] 压力测试：并发 50 节点 × 10 任务/分钟
- [ ] 容灾测试：断线重连、网络抖动
- [ ] 性能对比：WS 推送 vs HTTP 轮询 延迟数据

---

## 4. 工作量评估

| Phase | 内容 | 工作量 |
|-------|------|--------|
| Phase 0 | 基础准备 | 2h |
| Phase 1 | Gateway 侧推送 | 4h |
| Phase 2 | Worker 侧接收 | 4h |
| Phase 3 | 可靠性增强 | 3h |
| Phase 4 | 兼容与回退 | 2h |
| Phase 5 | 测试与优化 | 3h |
| **合计** | | **~18h（约 2 个工作日）** |

---

## 5. 风险与注意事项

### 5.1 技术风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| WS 连接不稳定 | 推送失败 | 已有 HTTP poll 兜底 |
| 旧 Worker 不兼容 | 消息被忽略 | msg_type 未知时 default 跳过 |
| 消息堆积 | 内存/性能 | 限流 + 队列容量限制 |
| 并发冲突 | 任务重叠 | Worker 侧 concurrent 限制 |
| 跨平台差异 | Android/Win/Linux | 全平台测试 |

### 5.2 已知约束

1. **gorilla/websocket 不支持并发写** — 已有 `wsMu` 锁解决
2. **Worker 节点 IP 动态变化** — WS 连接是唯一的身份标识，不依赖 IP
3. **Android 节点网络弱** — WS 自动重连已有实现
4. **Windows 节点 chcp 编码** — 命令执行前设置 utf-8 编码

---

## 6. 后续规划（不在本版本范围）

1. **任务分片**: 大任务拆分成子任务并行执行
2. **任务优先级队列**: 不同来源不同优先级调度
3. **Agent 集成**: Worker 收到任务后可自动触发 Agent 分析结果
4. **可视化**: 实时任务看板

---

## 7. 附录

### 7.1 现有 WS 消息类型

| msg_type | 用途 | 方向 |
|----------|------|------|
| `register` | Worker 注册 | Worker → Gateway |
| `register_ack` | 注册确认 | Gateway → Worker |
| `pong` | 心跳响应 | Worker → Gateway |
| `hall` / `hall_message` | 群聊消息 | 双向 |
| `arc_net` | 节点广播 | Gateway → Worker |

### 7.2 新增消息类型

| msg_type | 用途 | 方向 |
|----------|------|------|
| `task_message` | 任务下发 | Gateway → Worker |
| `task_result` | 结果上报 | Worker → Gateway |
| `task_ack` | 任务确认 | Worker → Gateway |
| `task_timeout` | 超时告警 | Gateway → Worker |

---

*Draft v0.1 — 待评审后进入实施*
