# SPEC-TASK-WS-001: 基于 WebSocket 的实时任务分发

**版本**: v1.0-draft  
**日期**: 2026-06-13  
**状态**: 设计提案  
**作者**: 小智（调度）  
**相关规范**: SPEC-WS-001 (WebSocket 通信协议)

---

## 1. 背景与问题

### 1.1 现状

当前 ComputeHub 任务调度采用 **HTTP 轮询 + submit** 模式：

```
┌──────────┐     POST     ┌────────────┐     HTTP GET     ┌──────────┐
│ Gateway  │ ───────────► │ Task Queue │ ◄─────────────── │ Worker   │
│          │              │            │   /api/v1/hall   │ (poll)   │
│          │              │            │   /poll          │          │
│          │              │            │                  │          │
│          │ ◄────────────│            │                  │          │
│          │  Result      │            │                  │          │
└──────────┘              └────────────┘                  └──────────┘
```

- Worker 启动 WS 连接 → 用于 **Hall 群聊** + **ARC-NET 广播**
- 任务分发 → `/api/v1/tasks/submit` → Worker 通过 Hall poll 被动拉取
- 没有**实时任务推送**能力

### 1.2 痛点

| 问题 | 说明 |
|------|------|
| **延迟高** | Worker 轮询间隔 3-10s，任务下发有秒级延迟 |
| **无优先级推送** | 所有消息走同一个 Hall 通道，任务无优先级 |
| **状态不可见** | Gateway 不知道 Worker 何时"看到"了任务 |
| **长连接浪费** | WS 已建立，但只用于群聊，任务仍需 HTTP 轮询 |
| **断线重传** | WS 断线后，轮询恢复慢 |

### 1.3 目标

通过 WS 长连接实现**实时任务推送**：
- 任务提交后立即推送到目标 Worker
- 端到端延迟 < 200ms
- 支持任务优先级 + 状态回传
- 保持 Hall 群聊与任务通道分离

---

## 2. 架构设计

### 2.1 消息流

```
┌──────────┐   POST submit    ┌────────────┐   WS 推送   ┌──────────┐
│ Gateway  │ ────────────────► │ Task Queue │ ──────────► │ Worker   │
│          │                   │            │             │ (WS)    │
│          │ ◄─────────────── │            │ ◄─────────  │          │
│          │  Result/Progress │            │  TaskDone   │          │
│          │                   │            │             │          │
└──────────┘                   └────────────┘             └──────────┘
```

### 2.2 消息类型

在现有 WS 消息类型基础上增加：

| msg_type | 方向 | 说明 |
|----------|------|------|
| `hall` / `hall_message` | bidirectional | 群聊消息（现有） |
| `arc_net` | gateway → workers | 广播（现有） |
| `task_submit` | gateway → worker | **新** 任务下发 |
| `task_result` | worker → gateway | **新** 任务结果回传 |
| `task_progress` | worker → gateway | **新** 任务进度更新 |
| `task_cancel` | gateway → worker | **新** 任务取消 |

### 2.3 任务消息结构

#### 2.3.1 task_submit（下发）

```json
{
  "msg_type": "task_submit",
  "task_id": "task-xxx",
  "node_id": "worker-arm",
  "command": "uname -a",
  "timeout": 30,
  "priority": 5,
  "submitted_at": "2026-06-13T06:48:00+08:00",
  "source_type": "api",
  "env_vars": {}
}
```

#### 2.3.2 task_result（回传）

```json
{
  "msg_type": "task_result",
  "task_id": "task-xxx",
  "success": true,
  "exit_code": 0,
  "stdout": "Linux android...",
  "stderr": "",
  "duration": "104ms",
  "executed_on": "worker-arm",
  "completed_at": "2026-06-13T06:48:01+08:00"
}
```

#### 2.3.3 task_progress（进度）

```json
{
  "msg_type": "task_progress",
  "task_id": "task-xxx",
  "status": "running",
  "stdout_partial": "...",
  "stderr_partial": "...",
  "progress": 50
}
```

#### 2.3.4 task_cancel（取消）

```json
{
  "msg_type": "task_cancel",
  "task_id": "task-xxx"
}
```

---

## 3. Gateway 端改动

### 3.1 文件: `src/gateway/gateway_ws.go`

#### 3.1.1 新增 SendTask 方法

在 `WSHub` 上增加任务推送方法：

```go
// SendTask 向指定节点推送任务
func (h *WSHub) SendTask(nodeID string, task *kernel.TaskSubmit) error {
    client := h.GetClient(nodeID)
    if client == nil {
        return fmt.Errorf("node %s not connected via WS", nodeID)
    }
    
    wsMsg := &WSMessage{
        MsgType:   "task_submit",
        SenderID:  "gateway",
        TaskID:    task.TaskID,
        Timestamp: time.Now().UnixMilli(),
        Payload:   marshalTask(task),
    }
    
    return client.send(wsMsg)
}

// SendTaskToAll 广播任务给所有节点（auto-schedule 场景）
func (h *WSHub) SendTaskToAll(task *kernel.TaskSubmit) error {
    wsMsg := &WSMessage{
        MsgType:   "task_submit",
        SenderID:  "gateway",
        TaskID:    task.TaskID,
        Timestamp: time.Now().UnixMilli(),
        Payload:   marshalTask(task),
    }
    return h.FanOutAll(wsMsg, "gateway")
}
```

#### 3.1.2 修改 readPump 接收 task_result / task_progress

```go
func (h *WSHub) readPump(client *WSClient) {
    // ... 现有代码 ...
    
    case "task_result":
        // 解析任务结果，更新 Kernel task queue
        var taskResult kernel.TaskResult
        json.Unmarshal(msg.Payload, &taskResult)
        h.gateway.handleTaskResult(taskResult)
        
    case "task_progress":
        var progress kernel.TaskProgress
        json.Unmarshal(msg.Payload, &progress)
        h.gateway.handleTaskProgress(progress)
        
    case "task_submit", "task_cancel":
        // 忽略来自 worker 端的这些类型（它们只接收）
        
    default:
        // 现有 hall/arc_net 逻辑
}
```

### 3.2 文件: `src/gateway/gateway.go`

#### 3.2.1 修改 handleTaskSubmit

当任务提交时，检查目标节点的 WS 连接状态：

```go
func (g *OpcGateway) handleTaskSubmit(w http.ResponseWriter, r *http.Request) {
    // ... 现有解析逻辑 ...
    
    // 提交到 queue
    taskId := g.Kernel.TaskQueue.Submit(task)
    
    // 优先通过 WS 推送（实时）
    if g.wsHub != nil {
        if task.AssignedNode != "" {
            // 点对点推送
            err := g.wsHub.SendTask(task.AssignedNode, task)
            if err == nil {
                g.sendResponse(w, Response{
                    Success: true,
                    Data:    map[string]string{"task_id": taskId, "delivery": "ws"},
                })
                return
            }
            // WS 失败，降级 HTTP
        } else {
            // 广播给所有节点
            g.wsHub.SendTaskToAll(task)
        }
    }
    
    // WS 不可用时，降级到现有 HTTP 方式
    g.pushViaHTTP(task)
    
    g.sendResponse(w, Response{
        Success: true,
        Data:    map[string]string{"task_id": taskId, "delivery": "http"},
    })
}
```

#### 3.2.2 新增处理函数

```go
func (g *OpcGateway) handleTaskResult(tr kernel.TaskResult) {
    g.Kernel.TaskQueue.CompleteTask(tr)
    // 可选：广播给其他节点（进度同步）
    g.broadcastTaskStatus(tr)
}

func (g *OpcGateway) handleTaskProgress(tp kernel.TaskProgress) {
    g.Kernel.TaskQueue.UpdateProgress(tp)
}
```

---

## 4. Worker 端改动

### 4.1 文件: `src/workercmd/worker_hall_client.go`

#### 4.1.1 修改 wsReadLoop

增加 task 消息类型处理：

```go
func (hc *HallClient) wsReadLoop() {
    // ... 现有代码 ...
    
    switch envelope.MsgType {
    case "ping":
        // 现有 ping 逻辑
    
    case "hall", "hall_message":
        // 现有 hall 逻辑
    
    case "arc_net":
        // 现有 arc_net 逻辑
    
    case "task_submit":
        // 新：接收任务下发
        var task kernel.TaskSubmit
        json.Unmarshal(envelope.Payload, &task)
        hc.handleTaskSubmit(&task)
    
    case "task_cancel":
        var cancel kernel.TaskCancel
        json.Unmarshal(envelope.Payload, &cancel)
        hc.handleTaskCancel(&cancel)
    
    default:
        // 现有未知消息日志
    }
}
```

#### 4.1.2 新增任务处理方法

```go
// handleTaskSubmit 接收任务并开始执行
func (hc *HallClient) handleTaskSubmit(task *kernel.TaskSubmit) {
    fmt.Printf(" [HallClient:%s] 📥 收到任务: %s cmd=%s priority=%d\n",
        hc.nodeID, task.TaskID, task.Command, task.Priority)
    
    // 提交到 executor queue
    hc.executor.Dispatch(task)
}

// handleTaskCancel 取消任务
func (hc *HallClient) handleTaskCancel(cancel *kernel.TaskCancel) {
    hc.executor.Cancel(cancel.TaskID)
}

// sendTaskResult 通过 WS 发送任务结果
func (hc *HallClient) sendTaskResult(result *kernel.TaskResult) {
    wsMsg := &WSMessage{
        MsgType:   "task_result",
        SenderID:  hc.nodeID,
        TaskID:    result.TaskID,
        Timestamp: time.Now().UnixMilli(),
        Payload:   marshalTaskResult(result),
    }
    hc.wsMu.Lock()
    defer hc.wsMu.Unlock()
    hc.wsConn.WriteJSON(wsMsg)
}

// sendTaskProgress 通过 WS 发送任务进度
func (hc *HallClient) sendTaskProgress(progress *kernel.TaskProgress) {
    wsMsg := &WSMessage{
        MsgType:   "task_progress",
        SenderID:  hc.nodeID,
        TaskID:    progress.TaskID,
        Timestamp: time.Now().UnixMilli(),
        Payload:   marshalTaskProgress(progress),
    }
    hc.wsMu.Lock()
    defer hc.wsMu.Unlock()
    hc.wsConn.WriteJSON(wsMsg)
}
```

### 4.2 文件: `src/workercmd/worker_kernel.go`

#### 4.2.1 修改 executor 接口

```go
type Executor struct {
    // 现有字段...
}

// Dispatch 接收任务（从 WS 推送）
func (e *Executor) Dispatch(task *kernel.TaskSubmit) {
    // 检查是否在队列中
    if e.IsQueued(task.TaskID) {
        return // 避免重复
    }
    e.Submit(task)
}

// Cancel 取消任务
func (e *Executor) Cancel(taskID string) {
    e.CancelTask(taskID)
}
```

---

## 5. 降级与兼容

### 5.1 降级策略

```
任务提交 → WS 推送 → 
  ├─ 成功 → 立即返回 task_id + "delivery": "ws"
  └─ 失败 (节点无 WS 连接 / 推送超时 2s) → HTTP fallback
     └─ 通过现有 HTTP poll 推送 → 返回 task_id + "delivery": "http"
```

### 5.2 向后兼容

- 旧版 Worker 不支持 WS 任务消息 → 自动走 HTTP poll（现有逻辑不变）
- 新版 Worker 优先 WS → 失败自动降级 HTTP
- Gateway 同时支持 WS 推送和 HTTP poll，不影响现有行为

### 5.3 超时保护

- WS 推送超时 2s → 立即走 HTTP fallback
- 任务 executor 收到 `task_submit` 后立即 ACK → Gateway 知道推送成功

---

## 6. 实施计划

### Phase 1: 基础推送（P0）— 预计 2-3 小时

| 步骤 | 文件 | 改动 | 估时 |
|------|------|------|------|
| 1 | `gateway_ws.go` | 新增 `SendTask()` 方法 | 30min |
| 2 | `gateway.go` | `handleTaskSubmit` 增加 WS 推送 + 降级 | 45min |
| 3 | `worker_hall_client.go` | wsReadLoop 增加 `task_submit` 处理 | 30min |
| 4 | `worker_kernel.go` | executor.Dispatch() 接收推送 | 30min |
| 5 | 全平台编译 + 部署 | 验证 | 30min |

### Phase 2: 结果回传（P1）— 预计 2-3 小时

| 步骤 | 文件 | 改动 | 估时 |
|------|------|------|------|
| 1 | `worker_hall_client.go` | 新增 `sendTaskResult()` WS 回传 | 30min |
| 2 | `worker_kernel.go` | executor 完成后主动 WS 推送结果 | 30min |
| 3 | `gateway_ws.go` | readPump 接收 `task_result` | 20min |
| 4 | `gateway.go` | handleTaskResult 更新 queue | 20min |
| 5 | 编译 + 验证 | 端到端测试 | 30min |

### Phase 3: 进度推送 + 取消（P2）— 预计 1-2 小时

| 步骤 | 改动 |
|------|------|
| 1 | task_progress 实时推送（Streaming 输出） |
| 2 | task_cancel 实时取消 |
| 3 | 优先级队列优化 |

---

## 7. 风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| WS 连接不稳定 | 推送失败 | 自动降级 HTTP |
| Worker 执行阻塞 | 任务堆积 | 已有 concurrent=8 限制 |
| 重复任务 | 同一任务多次推送 | 去重逻辑（task_id 检查） |
| 大文件任务 | WS 消息过大 | 走 Gallery 传输 + WS 只传元信息 |
| 兼容旧版本 Worker | 功能不完整 | WS 推送失败自动 HTTP fallback |

---

## 8. 验收标准

- [ ] Gateway 提交任务后，目标 Worker **< 200ms** 收到任务
- [ ] Worker 执行完成后，**主动推送**结果到 Gateway
- [ ] WS 断线时自动降级到 HTTP poll
- [ ] 全 4 个节点（ecs-p2ph / worker-arm / windows-mobile / wanlida-opc01）均能接收任务
- [ ] 并发 8 任务不丢失、不重复
- [ ] 端到端延迟从 3-10s 降到 < 500ms

---

*设计草案 — 待讨论确认后实施*
