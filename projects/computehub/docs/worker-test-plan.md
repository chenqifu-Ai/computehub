# ComputeHub Worker — 测试规划书

## 1. 概述

### 1.1 当前状态

Worker Agent 是一个 776 行的 `main.go` 单体，直接运行在主协程。核心流程：

```
Register → Heartbeat Goroutine(10s) → TaskPoll Goroutine(5s) → FetchDetail → Execute → ReportResult
```

**当前问题**：

| 问题 | 影响 |
|------|------|
| 所有逻辑在 `main()` 中 | 无法单元测试 |
| HTTP 客户端硬编码 `&http.Client{}` | 不能注入 mock server |
| `exec.Command("nvidia-smi")` | 无 GPU 环境就挂 |
| `for {}` 死循环 | 天然不可测 |
| GPU 采集和命令执行耦合在一起 | 场景覆盖不了 |

### 1.2 目标

1. **可测试** — 100% 单元测试覆盖核心流程
2. **可 mock** — 无 GPU / 无网络也跑得起来
3. **可验证** — 每一行关键逻辑都有测试兜底

---

## 2. 重构方案

### 2.1 包结构

```
cmd/worker/main.go        # 仅剩 CLI 入口 + main()
src/worker/
├── worker.go              # Worker 核心结构体 + 生命周期
├── collector.go           # GPU/系统指标采集 (可 mock)
├── executor.go            # 命令执行器 (可 mock)
├── reporter.go            # 结果上报 (可 mock)
└── worker_test.go         # 单元测试
```

### 2.2 依赖注入

```go
// ── 核心接口 ──

// RegisterClient: 注册/心跳/注销 (控制面)
type RegisterClient interface {
    Register(req *RegisterReq) error
    Heartbeat(req *HeartbeatReq) error
    Unregister() error
}

// TaskClient: 任务拉取/详情/结果 (任务面)
type TaskClient interface {
    FetchTasks(nodeID string) ([]TaskInfo, error)
    FetchTaskDetail(taskID, nodeID string) (*TaskDetail, error)
    SubmitResult(result *TaskResult) error
}

// GPUCollector: GPU/系统指标采集 (可 mock)
type GPUCollector interface {
    Collect() (*GPUStats, error)
    DetectGPUType() (string, error)
    CountGPUs() int
}

// CommandExecutor: 命令执行 (可 mock)
type CommandExecutor interface {
    Execute(command string, timeout int) (*ExecResult, error)
}
```

### 2.3 Worker 结构体

```go
type Worker struct {
    nodeID        string
    config        Config
    registerCli   RegisterClient
    taskCli       TaskClient
    gpuCollector  GPUCollector
    cmdExecutor   CommandExecutor
    runningTasks   sync.Map
    taskCount     atomic.Int64
    stopCh        chan struct{}
}
```

---

## 3. 测试场景矩阵

### 3.1 注册 (Register)

| # | 场景 | Gateway 行为 | 预期结果 |
|---|------|-------------|----------|
| R1 | ✅ 首次注册成功 | 返回 `{"success":true}` | 日志 "节点已注册" |
| R2 | ✅ 重复注册 (幂等) | 返回 `{"error":"node already registered"}` | 不报错，继续 |
| R3 | ❌ Gateway 不可用 | 连接拒绝 | 重试 3 次后进入重试循环 |
| R4 | ❌ Gateway 返回 500 | HTTP 500 | 重试 |
| R5 | ✅ 自动补全 NodeID | 不传 `--node-id` | 生成 `worker-<hostname>` |

### 3.2 心跳 (Heartbeat)

| # | 场景 | 行为 | 预期结果 |
|---|------|------|----------|
| H1 | ✅ 普通心跳 | GPU 50%, 65°C | POST 成功，状态更新 |
| H2 | ✅ 高温告警 | GPU 92°C | 终端显示红色温度标记 |
| H3 | ✅ 高利用率 | GPU 95% | 显示 `🔴 95.0%` |
| H4 | ❌ 心跳失败 | Gateway 断连 | 打印错误日志，不退出 |
| H5 | ✅ 无 GPU 环境 | nvidia-smi 不可用 | 上报 CPU only，GPU 指标为 0 |
| H6 | ✅ 多 GPU | 4 块 H100 | 上报均值 |

### 3.3 任务轮询 (Task Poll)

| # | 场景 | Gateway 数据 | 预期结果 |
|---|------|-------------|----------|
| P1 | ✅ 无待处理任务 | 返回空列表 | 跳过，等 5s |
| P2 | ✅ 有新任务 | 1 个 pending 任务 | 拉取详情，开始执行 |
| P3 | ✅ 多个待处理任务 | 3 个 pending | 逐个处理 |
| P4 | ❌ Gateway 不可用 | 连接失败 | 重试 |
| P5 | ✅ 并发限制 | 已有 4 个 running | 跳过轮询，直到完成 |
| P6 | ✅ 任务已在执行 | 新轮询到同一任务 | 跳过（幂等） |

### 3.4 拉取详情 (Fetch Detail)

| # | 场景 | 行为 | 预期结果 |
|---|------|------|----------|
| D1 | ✅ 正常拉取 | 返回完整命令 | 进入 executeTask() |
| D2 | ❌ 任务不存在 | 返回 404 | 打印警告，继续轮询 |
| D3 | ❌ Gateway 超时 | 30s 无响应 | 超时返回错误 |

### 3.5 任务执行 (Execute)

| # | 场景 | 命令 | 预期结果 |
|---|------|------|----------|
| E1 | ✅ 成功 | `echo hello` | exit=0, stdout="hello" |
| E2 | ❌ 失败 | `exit 1` | exit=1, stderr 非空 |
| E3 | ❌ 超时 | `sleep 100` (timeout=1s) | SIGTERM → exit=-1 |
| E4 | ✅ 命令为空 | `""` | 跳过，不执行 |
| E5 | ❌ 非法命令 | `rm -rf /` | 正常执行（由 Gateway 安全层处理） |

### 3.6 结果回传 (Report)

| # | 场景 | Gateway 行为 | 预期结果 |
|---|------|-------------|----------|
| S1 | ✅ 成功回传 | 返回 `{"success":true}` | 日志 "任务完成 ✅" |
| S2 | ❌ 回传失败 | Gateway 断连 | 打印错误，本地报告已保存 |
| S3 | ✅ 本地报告保存 | 无 Gateway | 报告写入 `/tmp/computehub-worker/task-<id>-<ts>.json` |

### 3.7 Graceful Shutdown

| # | 场景 | 行为 | 预期结果 |
|---|------|------|----------|
| G1 | ✅ SIGTERM | kill 进程 | 注销节点，退出码 0 |
| G2 | ✅ SIGINT | Ctrl+C | 同上 |

---

## 4. 测试策略

### 4.1 测试金字塔

```
        ┌──────────────┐
        │  E2E 集成测试 │   ← 启动真实 Gateway + mock Worker
       ┌┴──────────────┴┐
       │  组件集成测试   │   ← httptest.Server + 真实 Worker
      ┌┴────────────────┴┐
      │   单元测试 (mock)  │   ← 所有接口都是 mock
      └──────────────────┘
```

### 4.2 本机测试（推荐方案）

在 **本机（没有 GPU）** 的测试方案：

```bash
# 1. 启动 Gateway（内存模式，无持久化）
go run ./cmd/gateway

# 2. 启动 Worker（指向本机 Gateway，GPU 类型指定为 CPU）
go run ./cmd/worker \
  --gw http://localhost:8282 \
  --node-id test-worker-1 \
  --gpu-type CPU \
  --region cn-east

# 3. 提交一个测试任务
curl -X POST http://localhost:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-001",
    "source_type": "manual",
    "priority": 5,
    "command": "echo hello from worker",
    "timeout": 30,
    "assigned_nodes": ["test-worker-1"]
  }'

# 4. 查看结果
curl http://localhost:8282/api/v1/tasks/list | jq .
```

**测试脚本**：

```bash
# test/e2e/worker-basic.sh
#!/bin/bash
set -e

echo "=== ComputeHub Worker E2E Test ==="

# Start Gateway in background
go run ./cmd/gateway --port 18282 > /tmp/gw.log 2>&1 &
GW_PID=$!
sleep 2

# Start Worker
go run ./cmd/worker \
  --gw http://localhost:18282 \
  --node-id e2e-worker \
  --gpu-type CPU \
  --interval 1 \
  --heartbeat 2 \
  --concurrent 2 > /tmp/worker.log 2>&1 &
WORKER_PID=$!
sleep 2

# Submit task
curl -s -X POST http://localhost:18282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"task_id":"e2e-001","command":"echo test-ok","priority":5,"assigned_nodes":["e2e-worker"]}'

# Wait for execution
sleep 5

# Verify result
curl -s http://localhost:18282/api/v1/tasks/list | grep -q '"status":"completed"'
echo "✅ Task completed"

# Cleanup
kill $WORKER_PID $GW_PID 2>/dev/null
echo "=== E2E Test PASSED ==="
```

### 4.3 单元测试（Go test）

使用 `httptest.Server` mock Gateway，`gomock` 或手写 mock 替代 GPU 采集和命令执行。

**核心测试框架**：

```go
func setupWorkerTest(t *testing.T) (*httptest.Server, *Worker, *mockGpuCollector, *mockCmdExecutor) {
    // 1. 创建 Gateway（用真实实现，纯内存模式）
    gw := gateway.NewOpcGateway(0, &gateway.GatewayConfig{
        GeneStorePath: "/tmp/test-genes.json",
        SandboxPath:   "/tmp/opc-sandbox",
        MaxNodes:      10,
    })
    ts := httptest.NewServer(gw)

    // 2. 创建 mock 组件
    mockGpu := &mockGpuCollector{
        stats: &GPUStats{Utilization: 50, Temperature: 65, Count: 1},
    }
    mockCmd := &mockCmdExecutor{}

    // 3. 创建 Worker（注入 mock）
    w := NewWorker(Config{
        GatewayURL: ts.URL,
        NodeID:     "test-node",
        GPUType:    "CPU",
        PollInterval: time.Second,
        HeartbeatInterval: 2 * time.Second,
    })
    w.gpuCollector = mockGpu
    w.cmdExecutor = mockCmd
    w.client = ts.Client()

    return ts, w, mockGpu, mockCmd
}
```

### 4.4 测试用例（Ginkgo / 纯 Go `testing` 包）

**推荐纯 `testing` 包**——减少依赖，项目当前也用这个模式：

```go
// Test: 注册成功
func TestWorker_Register_Success(t *testing.T) {
    ts, w, _, _ := setupWorkerTest(t)
    defer ts.Close()

    err := w.Register()
    if err != nil {
        t.Fatalf("Register failed: %v", err)
    }
}

// Test: 重复注册（幂等）
func TestWorker_Register_Idempotent(t *testing.T) {
    ts, w, _, _ := setupWorkerTest(t)
    defer ts.Close()

    w.Register()  // first
    err := w.Register()  // second
    if err != nil {
        t.Fatalf("Second register should be idempotent: %v", err)
    }
}

// Test: Gateway 不可用
func TestWorker_Register_GatewayDown(t *testing.T) {
    w := NewWorker(Config{
        GatewayURL: "http://localhost:19999",
        NodeID:     "test-node",
    })
    err := w.Register()
    if err == nil {
        t.Fatal("Expected error when gateway is down")
    }
}

// Test: 心跳上报
func TestWorker_Heartbeat(t *testing.T) {
    ts, w, mockGpu, _ := setupWorkerTest(t)
    defer ts.Close()

    w.Register()  // must register first
    err := w.Heartbeat()
    if err != nil {
        t.Fatalf("Heartbeat failed: %v", err)
    }

    // Verify metrics via Gateway API
    resp, _ := http.Get(ts.URL + "/api/v1/nodes/metrics?node_id=test-node")
    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    if result["success"] != true {
        t.Fatal("Metrics not updated after heartbeat")
    }
}

// Test: 轮询拉取任务
func TestWorker_PollTasks_NewTaskFound(t *testing.T) {
    ts, w, _, _ := setupWorkerTest(t)
    defer ts.Close()

    w.Register()

    // Manually submit a task via Gateway API
    http.Post(ts.URL+"/api/v1/tasks/submit", "application/json",
        bytes.NewBuffer([]byte(`{"task_id":"t1","command":"echo ok","priority":5}`)))

    tasks, err := w.FetchTasks()
    if err != nil {
        t.Fatalf("FetchTasks failed: %v", err)
    }
    if len(tasks) == 0 {
        t.Fatal("Expected tasks, got none")
    }
}

// Test: 任务执行成功
func TestWorker_ExecuteTask_Success(t *testing.T) {
    ts, w, _, mockCmd := setupWorkerTest(t)
    defer ts.Close()

    mockCmd.result = &ExecResult{ExitCode: 0, Stdout: "hello", Duration: 100 * time.Millisecond}

    task := &TaskDetail{
        TaskID: "t1", Command: "echo hello", Timeout: 30,
    }
    
    result := w.ExecuteTask(task)
    if !result.Success {
        t.Fatalf("Task should succeed: exit=%d, stderr=%s", result.ExitCode, result.Stderr)
    }
    if result.Stdout != "hello" {
        t.Fatalf("Expected stdout 'hello', got '%s'", result.Stdout)
    }
}

// Test: 超时终止
func TestWorker_ExecuteTask_Timeout(t *testing.T) {
    mockCmd := &mockCmdExecutor{
        delay: 5 * time.Second, // will timeout
    }
    w := createWorkerWithMockCmd(mockCmd)

    task := &TaskDetail{TaskID: "t1", Command: "sleep 100", Timeout: 1}
    result := w.ExecuteTask(task)
    if result.Success {
        t.Fatal("Task should fail with timeout")
    }
}

// Test: 并发控制
func TestWorker_ConcurrencyLimit(t *testing.T) {
    _, w, _, _ := setupWorkerTest(t)
    
    // Simulate 4 running tasks
    for i := 0; i < 4; i++ {
        w.runningTasks.Store(fmt.Sprintf("task-%d", i), true)
    }
    
    if w.CanAcceptTask() {
        t.Fatal("Should not accept task when at concurrency limit")
    }
}

// Test: 注销
func TestWorker_Unregister(t *testing.T) {
    ts, w, _, _ := setupWorkerTest(t)
    defer ts.Close()

    w.Register()
    err := w.Unregister()
    if err != nil {
        t.Fatalf("Unregister failed: %v", err)
    }
}
```

---

## 5. 测试数据与 Mock

### 5.1 Mock GPUCollector

```go
type mockGpuCollector struct {
    stats    *GPUStats
    gpuType  string
    gpuCount int
    err      error
}

func (m *mockGpuCollector) Collect() (*GPUStats, error) {
    if m.err != nil {
        return nil, m.err
    }
    return m.stats, nil
}

func (m *mockGpuCollector) DetectGPUType() (string, error) {
    return m.gpuType, nil
}

func (m *mockGpuCollector) CountGPUs() int {
    return m.gpuCount
}
```

### 5.2 Mock CommandExecutor

```go
type mockCmdExecutor struct {
    result *ExecResult
    err    error
    delay  time.Duration
    mu     sync.Mutex
    calls  []string  // 记录所有调用，便于断言
}

func (m *mockCmdExecutor) Execute(cmd string, timeout int) (*ExecResult, error) {
    m.mu.Lock()
    m.calls = append(m.calls, cmd)
    m.mu.Unlock()

    if m.delay > 0 {
        time.Sleep(m.delay)
    }
    if m.err != nil {
        return nil, m.err
    }
    return m.result, nil
}
```

---

## 6. CLI 测试验证清单

测试完成后，手动验证以下场景：

```bash
# ── 启动环境 ──
go run ./cmd/gateway --port 8282 &
sleep 2

# ── 1. 默认启动 Worker ──
go run ./cmd/worker
# 预期: 自动检测系统，显示 node=worker-<hostname>, GPU=CPU, Region=cn-east

# ── 2. 指定参数启动 ──
go run ./cmd/worker \
  --gw http://localhost:8282 \
  --node-id gpu-01 \
  --gpu-type CPU \
  --region cn-east \
  --interval 3 \
  --heartbeat 5

# ── 3. 帮助信息 ──
go run ./cmd/worker --help
# 预期: 显示参数说明

# ── 4. 提交任务 ──
curl -X POST http://localhost:8282/api/v1/tasks/submit \
  -d '{"task_id":"t1","command":"date","priority":5,"assigned_nodes":["gpu-01"]}'

# ── 5. 查看状态 ──
curl http://localhost:8282/api/status | jq .
curl http://localhost:8282/api/v1/nodes/list | jq .
curl http://localhost:8282/api/v1/tasks/list | jq .
```

---

## 7. 实施步骤

| 步骤 | 内容 | 预计工时 |
|------|------|----------|
| 1. 重构 | `cmd/worker/main.go` → `src/worker/` 包 | 30 min |
| 2. 接口定义 | RegisterClient / TaskClient / GPUCollector / CommandExecutor | 10 min |
| 3. Mock 实现 | mock struct + 工厂函数 | 15 min |
| 4. 单元测试 | 注册/心跳/轮询/执行/超时/并发/注销 各场景 | 30 min |
| 5. 本地 E2E 脚本 | `test/e2e/worker-basic.sh` | 10 min |
| 6. 跑通验证 | `go test ./src/worker/ -v` + E2E 脚本运行 | 10 min |
| **合计** | | **~105 min** |

---

## 8. 风险与预案

| 风险 | 影响 | 预案 |
|------|------|------|
| 重构破坏现有功能 | Worker 启动不了 | 保留原有 `cmd/worker/main.go.bak` |
| Gateway 缺少某些 API 端点 | 测试通不过 | 先检查 `handleTaskDetail`, `handleTaskList` 响应格式 |
| `nvidia-smi` 本机不可用 | GPU 相关测试不通 | GPU 指标全 mock，本机 E2E 指定 `--gpu-type CPU` |
| 测试文件过大 | 维护困难 | 按功能拆为 `register_test.go`, `heartbeat_test.go`, `execute_test.go` |
