# ComputeHub — 确定性算力调度平台

> **使命**: 将全球分散的算力资源，整合为一张可承诺、可监控、可验证的确定性算力网络。
> **定位**: 不是 AI 框架，不是云平台，而是**算力操作系统**——让不同规模、不同地域、不同厂商的 GPU/CPU 资源像水电一样被调度。

---

## 一、架构总览

```
Phase 4: 可视化层 (Visualizer)
├── 全球算力地图 (Global Power Map)
├── GPU 实时监控看板
├── 节点发现雷达
└── WebSocket 实时推送
API: /api/v2/map/*, /api/v2/gpu/*, /ws/visual

Phase 3: 任务编排层 (TaskComposer)
├── 大模型拆解 (Decomposer) → 子任务列表
├── 并行分发引擎 (DispatchEngine) → 小模型并行执行
└── 大模型汇总 (Compositor) → 最终结果

Phase 2: 智能调度层 (Scheduler)
├── 区域感知调度 (latency-aware)
├── 区域熔断器 (circuit breaker)
├── 健康检查 (health check)
├── 节点发现 (node discovery)
├── GPU 监控 (GPU monitor)
└── 优先级队列 (priority queue)

Phase 1: 确定性内核层 (Kernel)
├── 线性化命令队列 (linear queue)
├── 状态快照/回滚 (state mirror)
├── 净化管道 (pure pipeline, 4 层 filter)
├── 基因存储 (gene store, 指令缓存)
├── 物理执行器 (executor, sandbox 隔离)
└── REST 网关 (HTTP API)
```

---

## 二、当前完成状态 (2026-04-25)

### Phase 1 — 确定性内核 ✅ 完成
| 组件 | 文件 | 测试 | 状态 |
|------|------|------|------|
| 线性内核 | kernel/kernel.go | — | ✅ |
| 算力 Action | kernel/actions.go | 17 test ✅ | ✅ |
| 净化管道 | pure/pipeline.go | — | ✅ |
| 基因存储 | gene/store.go | — | ✅ |
| 物理执行器 | executor/executor.go | — | ✅ |
| 网关 | gateway/gateway.go | 8/9 ✅ | ✅ |
| 权限/状态机 | api/ | 2 test ✅ | ✅ |

### Phase 2 — 智能调度 ✅ 完成
| 组件 | 文件 | 测试 | 状态 |
|------|------|------|------|
| 智能调度器 | scheduler/scheduler.go | 18 ✅ | ✅ |
| 区域熔断器 | scheduler/circuit_breaker.go | 14 ✅ | ✅ |
| 优先级队列 | scheduler/queue.go | 2 test ✅ | ✅ |
| 健康检查 | health/health.go | 12 ✅ | ✅ |
| 节点发现 | discover/discover.go | 14/15 ✅ | ✅ |
| GPU 监控 | monitor/monitor.go | 3 test ✅ | ✅ |

### Phase 3 — 任务编排 🟡 代码完成，待测试
| 组件 | 文件 | 状态 |
|------|------|------|
| TaskComposer | composer/composer.go | ✅ 编译通过 |
| — Decomposer | 同上 | ✅ 接口已实现 |
| — DispatchEngine | 同上 | ✅ 信号量控制并发 |
| — Compositor | 同上 | ✅ 接口已实现 |
| ⚠️ 测试 | composer/ | ❌ 未写 |

### Phase 4 — 可视化层 🟡 代码完成，待测试
| 组件 | 文件 | 状态 |
|------|------|------|
| GlobalPowerMap | visualizer/aggregator.go | ✅ 编译通过 |
| VisualizerGateway | visualizer/gateway.go | ✅ 编译通过 |
| — 全球算力地图 | /api/v2/map/global | ✅ |
| — GPU 实时看板 | /api/v2/gpu/realtime | ✅ |
| — 节点列表 | /api/v2/nodes | ✅ |
| — 告警列表 | /api/v2/alerts | ✅ |
| — WebSocket 推送 | /ws/visual | ✅ |
| — 模拟数据生成 | 模拟模式 | ✅ |
| ⚠️ 测试 | visualizer/ | ❌ 未写 |

### 项目统计
- 源码文件: 27 个 Go 文件 (含 10 个测试文件)
- 子包: 14 个 (api, composer, discover, executor, gateway, gene, health, kernel, monitor, pure, scheduler, visualizer)
- 测试: 约 90 个测试用例 (Phase 1+2 已有)

---

## 三、代码模块详解

### 3.1 Phase 1: Kernel
```
请求 → Pure Pipeline → Gene Store → OpcKernel → Executor
```
所有操作经过确定性路径，可追溯、可回滚。核心代码 kernel/kernel.go:
- NewKernel() → 初始化
- Start() → goroutine 处理
- Dispatch() → 提交命令

### 3.2 Phase 2: Scheduler
```
Scheduler 评分公式: 区域 40% + 延迟 30% + 负载 20% + 成功率 10%
```
- scheduler.go → scoreNode() 综合评分
- circuit_breaker.go → 三态切换
- discover.go → 广播/多播/手动发现
- health.go → TCP ping 真实延迟

### 3.3 Phase 3: Composer
```
大模型 (拆解) → N 个小模型 (并行) → 大模型 (汇总)
```
核心接口:
```go
type Decomposer interface { Decompose(input) (*DecomposedResult, error) }
type Compositor interface { Compose(task, results) (string, error) }
```
流程: Run() → 拆解 → DispatchEngine.Dispatch() → 汇总

### 3.4 Phase 4: Visualizer
```
GlobalPowerMap ← discover/health/monitor/scheduler → VisualizerGateway → REST + WebSocket
```
聚合引擎持有所有区域数据，订阅者模式支持实时推送。

---

## 四、API 端点一览

| 端点 | 方法 | 说明 | 阶段 |
|------|------|------|------|
| /api/dispatch | POST | 命令分发 | P1 |
| /api/health | GET | 系统健康 | P1 |
| /api/status | GET | 系统状态 | P1 |
| /api/v1/nodes/register | POST | 节点注册 | P2 |
| /api/v1/nodes/heartbeat | POST | 节点心跳 | P2 |
| /api/v1/nodes/list | GET | 节点列表 | P2 |
| /api/v1/nodes/metrics | GET | 节点指标 | P2 |
| /api/v1/tasks/submit | POST | 任务提交 | P2 |
| /api/v1/tasks/result | POST | 任务结果 | P2 |
| /api/v1/tasks/list | GET | 任务列表 | P2 |
| /api/v2/map/global | GET | 全球算力分布 | P4 |
| /api/v2/gpu/realtime | GET | GPU 实时看板 | P4 |
| /api/v2/nodes | GET | 节点列表 | P4 |
| /api/v2/alerts | GET | 告警列表 | P4 |
| /api/v2/health | GET | 系统健康 | P4 |
| /ws/visual | WS | 实时推送 | P4 |

---

## 五、下一步计划

### 优先级 P0 (本周)
- [ ] Phase 3 composer/ 测试覆盖
- [ ] Phase 4 visualizer/ 测试覆盖
- [ ] 全量 go test ./... 通过

### 优先级 P1
- [ ] 前端可视化面板 (全球算力地图)
- [ ] 真实节点接入验证
- [ ] API 文档 (OpenAPI 3.0)

### 优先级 P2 (长期)
- [ ] 多模型并行编排生产级实现
- [ ] 算力市场定价机制
- [ ] 跨集群联邦调度

---

## 六、工程结构

```
projects/computehub/
├── main.go                    # 统一入口
├── config.json                # 配置文件
├── go.mod / go.sum            # 依赖
├── src/                       # 14 个子包
│   ├── api/                   # 权限 + 状态机
│   ├── composer/              # Phase 3: 任务编排
│   ├── discover/              # Phase 2: 节点发现
│   ├── executor/              # Phase 1: 物理执行
│   ├── gateway/               # Phase 1: REST 网关
│   ├── gene/                  # Phase 1: 基因存储
│   ├── health/                # Phase 2: 健康检查
│   ├── kernel/                # Phase 1: 确定性内核
│   ├── monitor/               # Phase 2: GPU 监控
│   ├── pure/                  # Phase 1: 净化管道
│   ├── scheduler/             # Phase 2: 智能调度
│   └── visualizer/            # Phase 4: 可视化层
└── cmd/                       # (可选) 多入口
    ├── gateway/               # go run ./cmd/gateway
    └── tui/                   # go run ./cmd/tui
```

---

## 七、核心原则

1. **确定性第一** — 所有调度决策有公式、可追溯、可复现
2. **分层解耦** — 每层只依赖下层接口
3. **可观测** — 可视化层为"眼睛"
4. **容错至上** — 熔断、重试、超时、降级
5. **渐进演进** — Phase 1→4 逐步叠加，每阶段可独立运行

---

> **最后更新**: 2026-04-25 17:00
> **代码行数**: 27 个 Go 文件
> **编译状态**: ✅ go build ./... 通过
> **测试覆盖**: ~90 个测试用例 (Phase 1+2)
