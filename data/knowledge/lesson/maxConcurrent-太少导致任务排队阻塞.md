# Knowledge: maxConcurrent 太少导致任务排队阻塞
> Type: lesson
> Source: ecs-p2ph
> Confidence: 0.8
> TTL: 30 days
> Tags: 性能, 并发, 任务调度, Worker, Scheduler
> Timestamp: 2026-07-11T05:46:56+08:00

## Content

## maxConcurrent 太少导致任务排队阻塞

### 发现背景
老大在排查集群任务执行效率时发现，任务经常排队等待，节点明明空闲却不接新任务。

### 根因分析

**1. 默认值太小**
- Worker 默认 `MaxConcurrent = 4`（worker_main.go:80）
- 意味着每个节点最多同时跑 4 个任务
- 对于 GPU 节点（10×RTX4060）或快速任务（echo/ping），4 个并发远远不够

**2. 双重限制**
- **Worker 端**（worker_main.go:539）：`runningCount >= MaxConcurrent` → 直接 sleep 不轮询
- **Gateway 端**（scheduler/queue.go:181）：`ActiveTasks < MaxTasks` → 不派发新任务
- 两个限制叠加，任务排队更严重

**3. 节点间配置不一致**
- ecs-p2ph 手动设了 `--concurrent 8`
- 其他 5 个节点（fedroa-work1, xingke-work02, wanlida-work01, wanlida-ubuntu, windows-home-01）可能用的默认 4
- 没有统一管理机制

### 影响
- 任务排队时间变长
- 节点资源利用率低
- 快速任务（<1s）被慢任务阻塞
- 集群吞吐量受限

### 解决方案
1. **提高默认值**：`MaxConcurrent: 4` → `MaxConcurrent: 16`（或根据 CPU 核心数动态计算）
2. **按节点类型差异化**：GPU 节点 32+，CPU 节点 16，轻量节点 8
3. **配置统一管理**：在 config.json 中统一配置，Worker 启动时读取
4. **动态调整**：根据节点负载自动调整并发数

### 相关代码位置
- Worker 默认值：`src/workercmd/worker_main.go:80`
- Worker 并发限制：`src/workercmd/worker_main.go:539`
- Scheduler 派发限制：`src/scheduler/queue.go:181`
- CLI 参数：`--concurrent N`

### 发现者
老大 👑
