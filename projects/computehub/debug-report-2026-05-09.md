# ComputeHub 项目调试报告 (2026-05-09)

## 测试环境

| 节点 | 地址 | 角色 | 状态 |
|------|------|------|------|
| Gateway (本机) | 192.168.1.17:8282 | Gateway + TUI | ✅ 运行中 (PID 30745) |
| Gateway (远程) | 192.168.1.7:8282 | Gateway | ✅ 运行中 |
| Worker | cqf-worker-03 | Worker 节点 | ✅ online (但无 region/gpu 信息) |

---

## 1. 路由注册验证

### ✅ 所有 10 个路由均已实现且可用

| 路由 | 方法 | 处理器 | 状态 |
|------|------|--------|------|
| /api/v1/nodes/register | POST | handleNodeRegister | ✅ |
| /api/v1/nodes/unregister | POST | handleNodeUnregister | ✅ |
| /api/v1/nodes/heartbeat | POST | handleNodeHeartbeat | ✅ |
| /api/v1/nodes/list | GET | handleNodeList | ✅ |
| /api/v1/nodes/metrics | GET | handleNodeMetrics | ✅ |
| /api/v1/tasks/submit | POST | handleTaskSubmit | ✅ (有 bug) |
| /api/v1/tasks/result | POST | handleTaskResult | ✅ |
| /api/v1/tasks/cancel | POST | handleTaskCancel | ✅ |
| /api/v1/tasks/list | GET | handleTaskList | ✅ |
| /api/v1/tasks/detail | GET | handleTaskDetail | ✅ |
| /api/v1/tasks/poll | POST | handleTaskPoll | ✅ |
| /api/v1/tasks/progress | GET/POST | handleTaskProgress | ✅ |
| /api/v1/download | GET | handleFileDownload | ✅ |
| /api/v1/upgrade/check | GET | handleUpgradeCheck | ✅ |
| /api/v1/upgrade/config | GET | handleUpgradeConfig | ✅ |

### ⚠️ 路由重复注册（P1）

`Serve()` 和 `ServeWithServer()` 两个方法都注册了完全相同的路由。
- Serve(): 257-333 行
- ServeWithServer(): 307-333 行

如果两个方法都被调用，会导致 **路由重复注册，panic: pattern冲突**。
**但实际没 panic**，因为 Go 的 `http.ServeMux` 默认只有一个路由器，`Serve()` 中的 `http.HandleFunc` 注册在默认 mux 上，`ServeWithServer()` 也在同一个默认 mux 上注册，第二次调用会 panic。

**当前只调用了 `Serve()` 或 `ServeWithServer()` 中的一个**，所以暂时没出问题。

---

## 2. 🐛 Bug 发现

### 🔴 Bug 1: 任务提交返回空 task_id

```bash
# 提交任务
curl -X POST http://localhost:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"command":"echo hello","timeout":60,"priority":5}'

# 返回
{"success":true,"data":{"message":"task submitted","task_id":""},"error":"<nil>"}
```

**task_id 为空字符串**，但数据看起来成功了（success=true）。
任务列表显示所有节点的任务数组都是空的，说明 **任务提交后没有真正入队到 kernel 的优先级队列**。

**根因分析**：`handleTaskSubmit` 返回了 `task_id: ""`，说明 `Kernel.TaskQueue` 的 `Add` 方法没有正确生成/返回任务 ID，或者任务没有加入内核。

**影响**：
- Worker 无法认领任务（poll 返回空）
- 任务列表为空
- 整个任务流程断裂

### 🟡 Bug 2: cqf-worker-03 信息不完整

```json
{
  "node_id": "cqf-worker-03",
  "region": "",       // ❌ 空
  "gpu_type": "",     // ❌ 空
  "status": "online",
  "cpu_utilization": 0,
  "memory_used_gb": 0
}
```

worker-03 注册了但 **没有发送心跳更新指标**，也没有上报 GPU/区域信息。
需要确认 192.168.1.7 上的 worker 程序版本和行为。

### 🟡 Bug 3: Serve/ServeWithServer 代码重复

两个方法都注册了相同的路由，造成代码冗余。
如果以后有人调用 `Serve()` 又调用 `ServeWithServer()` 会 panic。

**建议**：抽出一个 `registerRoutes()` 私有方法，让两个方法都调用。

---

## 3. 已知待改进项（上次报告，仍未修复）

| 优先级 | 问题 | 状态 |
|--------|------|------|
| 🔴 P0 | 任务提交返回空 task_id | ❌ 未修复（**本次发现新 bug**） |
| 🔴 P0 | cqf-worker-03 信息不完整 | ⚠️ 无法远程 192.168.1.7 |
| 🟡 P1 | Serve/ServeWithServer 代码重复 | ❌ 未修复 |
| 🟡 P1 | 路由重复注册 | ❌ 未修复 |
| 🟢 P2 | cqf-worker-03 缺少 GPU/Region 信息 | ⚠️ 等待远程调试 |

---

## 4. Gateway 架构确认

### 配置文件
```json
{
  "gateway": { "port": 8282, "max_connections": 100 },
  "kernel": { "buffer_size": 100, "max_states": 1000 },
  "executor": { "sandbox_path": "/tmp/opc-sandbox" },
  "composer": {
    "api_url": "http://localhost:11434/v1",
    "model": "deepseek-v4-flash",
    "execute_models": ["deepseek-v4-flash", "qwen3.6-35b", "llama3.1:8b"],
    "max_concurrency": 8,
    "timeout_seconds": 120
  }
}
```

### 架构组件
- **Gateway**: HTTP API + WebSocket + Dashboard
- **Kernel**: 任务调度核心（优先级队列 + 节点管理）
- **Composer**: AI 模型调用层（Ollama）
- **Scheduler**: 调度策略（熔断 + 队列）
- **Visualizer**: 可视化聚合
- **Prometheus**: 指标导出

### 源码目录
```
src/
├── gateway/     (gateway.go, gateway_worker.go, gateway_upgrade.go)
├── kernel/      (kernel.go, actions.go)
├── composer/    (composer.go, client.go)
├── scheduler/   (scheduler.go, queue.go, circuit_breaker.go, preempt.go)
├── executor/    (executor.go)
├── discover/    (discovery.go)
├── visualizer/  (aggregator, bridge, gateway, prometheus)
├── health/      (health.go)
├── monitor/     (monitor.go)
├── gene/        (store.go)
├── api/         (permission.go, state_machine.go)
├── pure/        (pipeline.go)
├── prometheus/  (prometheus.go)
└── version/     (version.go)
```

---

## 5. 下一步

1. **🔴 修复 task_id 空值 bug** - 追踪 kernel/task 生成逻辑
2. **🟡 重构路由注册** - 抽 `registerRoutes()` 方法
3. **⚠️ 远程调试 cqf-worker-03** - 等 192.168.1.7 SSH 恢复
