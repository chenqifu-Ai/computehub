# TASK-Q-001: 直接节点分配 + 任务队列标准流程

**制定时间**: 2026-06-13  
**涉及功能**: `assigned_node` 直接分配 + 优先级队列 + WebSocket 重连后消息投递

## ✅ 验证结果 (2026-06-13 05:32)

### 测试场景
- **命令**: `echo test-pipeline-4060`
- **任务ID**: `task-1781299945733-673f1d`
- **目标节点**: `wanlida-opc01` (windows/amd64)
- **节点状态**: 注册中，WS 连接不稳定（频繁 reconnect）
- **结果**: ✅ 成功完成，exit code 0

### 执行时间线
```
05:32:24 - wanlida-opc01 WS 连接断开 (write failed)
05:32:25 - TASK_SUBMIT → Direct assignment → wanlida-opc01
05:32:25 - WS writePump 失败 (旧连接 closed network connection)
05:32:26 - wanlida-opc01 新 WS 连接建立
05:32:26 - TASK_RESULT 收到，处理成功
```

### 核心流程确认
1. ✅ `TASK_SUBMIT` 时 `assigned_node` 非空 → 直接分配到指定节点
2. ✅ 节点在线但 WS 不稳定 → 任务进入 `state.Tasks[taskID]` pending 状态
3. ✅ 节点重连 → 任务通过 WS 推送到节点
4. ✅ 节点执行完成 → `TASK_RESULT` 回传
5. ✅ Gateway 处理结果 → task 标记 completed

## 🔧 涉及文件

| 文件 | 职责 |
|------|------|
| `src/kernel/actions.go` | `AssignTaskToNode()` / `CompleteTask()` / `dispatchFromQueue()` |
| `src/api/state_machine.go` | `SubmitTaskRequest.AssignedNode` 字段 |
| `src/gateway/gateway.go` | `/api/v1/tasks` 端点，`assigned_node` 映射 |
| `src/workercmd/worker_kernel.go` | Worker 侧任务执行 + 结果回传 |

## ⚠️ 注意事项

1. **WS 不稳定时的任务可靠性**: 任务存在 Gateway 内存中，节点重连后可重新推送。但 Gateway 重启会丢失未执行的任务。
2. **节点不在线**: `assigned_node` 指定的节点必须注册且 online，否则 `SubmitTask` 直接返回错误。
3. **Capacity 检查**: 直接分配仍检查 `ActiveTasks < MaxTasks`，满负载会入队列或返回容量不足错误。
4. **兼容字段**: `node_id` / `node` 会自动映射到 `AssignedNode`，三者等价。

## 📋 标准操作流程

### 向指定节点提交任务
```
SubmitTaskRequest {
    "assigned_node": "wanlida-opc01",
    "command": "echo hello",
    "priority": 5
}
→ 成功: taskID + assigned node
→ 失败: 节点不在线/无容量
```

### 自动调度（不指定节点）
```
SubmitTaskRequest {
    "command": "echo hello",
    "priority": 5
}
→ Gateway 自动选择负载最低的在线节点
→ 所有节点繁忙时入优先级队列
```

## 🐛 已知限制

- Gateway 重启后未执行任务丢失（内存中）
- WS 频繁断连时任务推送有延迟（重连后重新推送）
- 无任务持久化/重试机制（仅内存队列）
