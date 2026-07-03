# OPC 架构决策记录 (Architecture Decision Records)

> **用途**: 给半年后的自己看。记录"为什么这样设计"，防止重复踩坑。
> **维护**: 每次重大架构变更时更新对应章节。
> **版本**: v1.3.14 (2026-06-05)

---

## ADR-001: 选择 Go 作为实现语言

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 项目启动时

### 背景

OPC 需要：
- 高并发（任务调度、Worker 心跳）
- 低延迟（Agent 响应）
- 跨平台（Linux/Windows/macOS/Android）
- 小 binary（部署到边缘设备）
- 快速开发迭代

### 决策

选择 Go 1.24 作为唯一实现语言。

### 理由

| 考量 | Go | Rust | Python | TypeScript |
|------|-----|------|--------|------------|
| 并发模型 | ✅ goroutine + channel | ✅ async/await | ❌ GIL 限制 | ⚠️ 单线程 |
| 编译产物 | ✅ 静态 binary | ✅ 静态 binary | ❌ 需要运行时 | ❌ 需要 Node.js |
| 跨平台 | ✅ 交叉编译无痛 | ⚠️ 需要 toolchain | ✅ 解释型 | ✅ 跨平台 |
| Binary 大小 | ✅ 10-20MB | ✅ 5-10MB | ❌ N/A | ❌ N/A |
| 开发速度 | ✅ 快速 | ❌ 慢 | ✅ 快速 | ✅ 快速 |
| 类型安全 | ⚠️ 弱类型 | ✅ 强类型 | ❌ 动态 | ⚠️ 可选 |
| 生态 | ✅ 丰富 | ⚠️ 较小 | ✅ 丰富 | ✅ 丰富 |

### 权衡

**放弃的东西**:
- Rust 的内存安全保证
- Python 的 AI/ML 生态（numpy、torch）
- TypeScript 的全栈统一

**换取的东西**:
- 一个 `go build` 命令搞定所有平台
- goroutine 天然适合任务调度
- 标准库强大（net/http、crypto、compress）

### 实际验证

- ✅ Termux (Android arm64) 上编译通过
- ✅ ECS (Linux amd64) 上编译通过
- ✅ Windows 交叉编译通过
- ✅ 单 binary 部署，无外部依赖

---

## ADR-002: 不用 Kubernetes

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 项目启动时

### 背景

K8s 是分布式系统的标准编排方案，提供：
- 自动扩缩容
- 服务发现
- 负载均衡
- 滚动更新

### 决策

不使用 K8s，自研轻量级调度系统。

### 理由

1. **规模不匹配**
   - OPC 节点数: 3-50 台（个人/小团队）
   - K8s 适合: 100-10000 台（企业级）
   - 引入 K8s 是"用牛刀杀鸡"

2. **复杂度爆炸**
   - K8s 本身需要 etcd、API server、kubelet、kube-proxy
   - 需要学习 YAML、Helm、RBAC、NetworkPolicy
   - 运维成本 > 开发成本

3. **功能不匹配**
   - OPC 需要: 任务队列 + Worker 心跳 + 升级管理
   - K8s 提供: Pod 编排 + Service mesh + Ingress
   - 90% 的 K8s 功能用不上

4. **Agent 集成困难**
   - K8s 没有内置 AI Agent 概念
   - 需要写 Operator + CRD，复杂度更高

### 权衡

**放弃的东西**:
- K8s 的自动扩缩容
- Service mesh 的流量管理
- 成熟的监控生态（Prometheus operator）

**换取的东西**:
- 代码量: ~3K 行（自研调度） vs 部署 K8s 集群
- 启动时间: 1 秒 vs K8s 集群启动 30 秒
- 运维: 0 人天 vs K8s 需要专人维护

### 实现细节

```
自研调度器 (src/scheduler/):
- 任务队列: 优先级 + FIFO
- 节点管理: 心跳 + 超时检测
- 负载均衡: round-robin / least-loaded / latency-aware
- 熔断器: 区域级失败率统计 + 自动熔断/恢复
```

### 何时重新评估

- 节点数 > 200 台
- 需要多租户隔离
- 需要自动扩缩容到云厂商

---

## ADR-003: 不用消息队列 (NATS/RabbitMQ/Kafka)

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 项目启动时

### 背景

分布式系统通常用消息队列解耦：
- Gateway → Queue → Worker
- 任务持久化
- 异步处理
- 背压控制

### 决策

不用外部消息队列，使用 Go channel + 内存队列。

### 理由

1. **单 Gateway 场景**
   - OPC 当前只有 1 个 Gateway（中心化）
   - 不需要多 Gateway 间的任务同步
   - 内存队列足够快

2. **简化部署**
   - 不引入外部依赖（NATS binary、RabbitMQ 集群）
   - 一个 `go run` 启动整个系统

3. **任务特性不同**
   - OPC 任务是"短命令"（< 300 秒）
   - 不需要持久化（失败重试即可）
   - 不需要 exactly-once 语义

4. **实时性要求**
   - Worker 轮询间隔: 3 秒
   - 消息队列的延迟优势不明显

### 权衡

**放弃的东西**:
- 任务持久化（Gateway 崩溃后任务丢失）
- 多 Gateway 水平扩展
- 背压控制（队列满时的处理）

**换取的东西**:
- 零外部依赖
- 启动时间: 1 秒 vs NATS 启动 2 秒 + 配置
- 内存占用: ~50MB vs NATS ~100MB

### 实现细节

```go
// Kernel 的线性化队列 (src/kernel/kernel.go)
type OpcKernel struct {
    LinearQueue chan Command  // 带缓冲的 channel
    // ...
}

// Worker 轮询模型 (src/workercmd/worker_main.go)
func (s *WorkerState) pollLoop() {
    ticker := time.NewTicker(3 * time.Second)
    for range ticker.C {
        task := s.pollTask()  // HTTP GET /api/v1/tasks/poll
        if task != nil {
            go s.executeTask(task)
        }
    }
}
```

### 已知问题

- ⚠️ Gateway 崩溃后，队列中未处理的任务丢失
- ⚠️ 没有任务持久化，重启后需要重新提交

### 何时重新评估

- 需要多 Gateway 高可用
- 任务数 > 10000 / 小时
- 需要 exactly-once 执行保证

---

## ADR-004: Agent 内置于 Worker，而非独立服务

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 2026-05 重构时

### 背景

AI Agent 可以部署为：
1. **独立服务**: Agent Server + Worker 分离
2. **内置模式**: Agent 嵌入 Worker binary

### 决策

Agent 内置于 Worker，每个 Worker 自带 AI 能力。

### 理由

1. **降低延迟**
   - Agent 直接调用本地 shell（0 网络延迟）
   - 独立服务需要: Agent → HTTP → Worker → 执行

2. **简化部署**
   - 一个 binary 同时提供: 任务执行 + AI Agent
   - 不需要部署两套服务

3. **上下文感知**
   - Agent 能直接访问 Worker 的状态（GPU 温度、负载）
   - 不需要通过 API 传递上下文

4. **离线能力**
   - Worker 可以在无网络环境下执行本地任务
   - 独立服务模式下，Agent Server 挂了所有 Worker 都傻

### 权衡

**放弃的东西**:
- Agent 的集中管理（每个 Worker 独立配置）
- Agent 的资源隔离（Agent 和 Worker 共享 CPU/内存）

**换取的东西**:
- 部署复杂度: 1 binary vs 2 binary
- 响应延迟: ~10ms (本地) vs ~50ms (网络)

### 实现细节

```go
// Worker 初始化时创建 Agent (src/workercmd/worker_main.go)
func (s *WorkerState) initAgent() {
    s.agent = agent.NewAgent(s.config.AgentModel, s.config.AgentAPIKey)
    s.agent.SetKernel(s.kernel)
    s.agent.SetNodeProvider(s.kernel.NodeMgr)
    
    // 注册工具
    s.agent.RegisterTool("exec_shell", s.toolExecShell)
    s.agent.RegisterTool("node_status", s.toolNodeStatus)
    // ...
}

// Agent 直接调用本地 shell
func (s *WorkerState) toolExecShell(ctx context.Context, params map[string]interface{}) (interface{}, error) {
    cmd := params["command"].(string)
    output, err := exec.Command("sh", "-c", cmd).Output()
    return map[string]string{"output": string(output)}, err
}
```

### 何时重新评估

- Agent 需要 GPU 推理（当前调用外部 API）
- Agent 之间需要协作（当前独立）
- 需要集中式 Agent 管理面板

---

## ADR-005: Gateway 单体架构，非微服务

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 项目启动时

### 背景

微服务架构将系统拆分为：
- 用户服务
- 任务服务
- 节点服务
- Agent 服务
- 监控服务

### 决策

Gateway 采用单体架构，所有功能在一个进程内。

### 理由

1. **团队规模**
   - 当前: 1 人开发
   - 微服务适合: 5+ 人团队并行开发

2. **部署复杂度**
   - 单体: 1 binary + 1 systemd service
   - 微服务: 5 binary + 服务发现 + 负载均衡 + API 网关

3. **调试困难**
   - 单体: 一个 debugger 搞定
   - 微服务: 分布式追踪（Jaeger、Zipkin）

4. **性能开销**
   - 单体: 函数调用（纳秒级）
   - 微服务: HTTP/gRPC（毫秒级）

### 权衡

**放弃的东西**:
- 独立扩缩容（不能只扩 Agent 服务）
- 故障隔离（一个模块崩了全崩）

**换取的东西**:
- 开发效率: 1 人搞定
- 部署复杂度: 1 systemd service
- 调试体验: 单步调试无压力

### 实现细节

```
Gateway 模块划分 (src/gateway/):
- gateway.go (1639 行): HTTP 路由 + 核心逻辑
- gallery.go (1000+ 行): 文件管理 + 视频生成
- gateway_worker.go: Worker 管理 + 任务分发
- gateway_upgrade.go: 升级管理
```

### 代码组织

虽然是单体，但通过包划分边界：
```
gateway.go      → HTTP 入口
kernel/         → 状态机 + 命令队列
scheduler/      → 调度策略
agent/          → AI Agent
composer/       → LLM 客户端
```

### 何时重新评估

- 团队 > 3 人
- 需要独立扩缩容某个模块
- 需要多语言实现（如 Python Agent）

---

## ADR-006: 线性化内核，非事件溯源

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 项目启动时

### 背景

状态管理有两种模式：
1. **事件溯源 (Event Sourcing)**: 记录所有事件，重放得到当前状态
2. **线性化队列**: 所有命令串行执行，状态即时更新

### 决策

使用线性化命令队列（`OpcKernel.LinearQueue`），不使用事件溯源。

### 理由

1. **复杂度**
   - 事件溯源需要: 事件存储 + 重放机制 + 快照
   - 线性化队列: 一个 channel + 一个 goroutine

2. **调试友好**
   - 事件溯源: 需要重放历史才能复现 bug
   - 线性化队列: 断点停在当前状态即可

3. **性能**
   - 事件溯源: 写事件 + 更新视图（双写）
   - 线性化队列: 直接更新状态（单写）

4. **当前规模**
   - 命令数: < 100 / 秒
   - 不需要审计所有历史

### 权衡

**放弃的东西**:
- 完整的审计日志
- 时间旅行调试（回到任意历史时刻）

**换取的东西**:
- 实现复杂度: 500 行 vs 5000 行
- 理解成本: 10 分钟 vs 1 天

### 实现细节

```go
// 所有命令串行执行，消除竞态
func (k *OpcKernel) Start() {
    go func() {
        for cmd := range k.LinearQueue {
            k.processCommand(cmd)  // 单 goroutine，无锁
        }
    }()
}

// 提交命令
func (k *OpcKernel) Dispatch(id, action string, payload interface{}) chan Response {
    respCh := make(chan Response, 1)
    k.LinearQueue <- Command{
        ID:       id,
        Action:   action,
        Payload:  payload,
        Response: respCh,
    }
    return respCh
}
```

### 何时重新评估

- 需要审计所有操作（合规要求）
- 需要"撤销"功能
- 需要多 Gateway 同步状态

---

## ADR-007: Pure Pipeline 输入验证

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 项目启动时

### 背景

输入验证可以：
1. 在每个 handler 里写 `if` 判断
2. 用 middleware 统一处理
3. 用 pipeline 模式分层过滤

### 决策

使用 Pure Pipeline（多级过滤器链）验证所有输入。

### 理由

1. **可组合性**
   - 过滤器可以任意组合
   - 新增验证规则只需添加一个 Filter

2. **可测试性**
   - 每个 Filter 独立测试
   - 不需要启动 HTTP server

3. **可读性**
   ```go
   p.AddFilter(&SyntaxFilter{})
   p.AddFilter(&SemanticFilter{AllowedActions: [...]})
   p.AddFilter(&BoundaryFilter{Blacklist: [...]})
   ```
   一眼看出验证流程。

### 实现细节

```go
// 过滤器接口 (src/pure/pipeline.go)
type PureFilter interface {
    Filter(input interface{}) FilterResult
    Name() string
}

// 语法过滤器：检查特殊字符、长度
type SyntaxFilter struct{}

// 语义过滤器：检查 action 是否允许
type SemanticFilter struct {
    AllowedActions []string
}

// 边界过滤器：检查黑名单路径
type BoundaryFilter struct {
    Blacklist []string
}

// 上下文过滤器：设备指纹
type ContextFilter struct {
    DeviceFingerprint string
}
```

### 权衡

**放弃的东西**:
- 简单场景下的直接 `if` 判断（更快）

**换取的东西**:
- 验证逻辑集中管理
- 新增规则: 加一个 Filter vs 改 10 个 handler

---

## ADR-008: Git 作为 Agent 记忆系统

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 2026-05

### 背景

Agent 需要长期记忆：
- 记住用户偏好
- 记住历史操作
- 跨会话保持上下文

传统方案：
- 向量数据库 (Pinecone、Weaviate)
- SQLite + FTS
- 文件系统

### 决策

使用 Git 作为 Agent 记忆系统（`src/agent/memory.go`，1630 行）。

### 理由

1. **版本控制**
   - 记忆自动有历史版本
   - 可以 `git log` 查看演变

2. **可搜索**
   - `git grep` 全文搜索
   - `git log --grep` 按时间过滤

3. **可备份**
   - `git push` 到远端即备份
   - 不需要额外备份脚本

4. **可审计**
   - 每条记忆都有 commit hash
   - 可以追溯"谁在什么时候加了什么"

5. **无外部依赖**
   - Git 是 Linux/macOS 标配
   - 不需要部署向量数据库

### 权衡

**放弃的东西**:
- 语义搜索（向量数据库的强项）
- 高并发写入（Git 不是为并发设计）

**换取的东西**:
- 部署复杂度: 0（Git 已安装）
- 运维成本: 0（不需要维护数据库）

### 实现细节

```go
// 记忆存储 (src/agent/memory.go)
type GitMemory struct {
    repoPath string  // /home/computehub/opc-memory
    // ...
}

// 添加记忆 → git commit
func (m *GitMemory) Add(memory string) error {
    // 写入文件
    os.WriteFile(filepath.Join(m.repoPath, "memories.md"), ...)
    
    // git add + commit
    exec.Command("git", "-C", m.repoPath, "add", ".").Run()
    exec.Command("git", "-C", m.repoPath, "commit", "-m", "Add memory").Run()
    
    return nil
}

// 搜索记忆 → git grep
func (m *GitMemory) Search(query string) ([]string, error) {
    output, _ := exec.Command("git", "-C", m.repoPath, "grep", query).Output()
    return strings.Split(string(output), "\n"), nil
}
```

### 何时重新评估

- 需要语义搜索（"找类似的记忆"）
- 记忆数 > 10000 条
- 需要多 Agent 共享记忆

---

## ADR-009: SafeCommand 绕过 seccomp (Termux/Android)

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 2026-06-03 (v1.3.13)

### 背景

在 Termux (Android) 上运行 OPC 时遇到 SIGSYS 崩溃：
```
fatal error: unexpected signal during runtime execution
[signal SIGSYS: bad system call]
```

根因：Go 的 `os/exec.LookPath` 使用 `faccessat2` 系统调用（syscall 439），被 Android seccomp 策略阻止。

### 决策

创建 `SafeCommand` 工具函数，绕过 `faccessat2`。

### 理由

1. **无法修改 seccomp**
   - Android 的 seccomp 策略由系统控制
   - 无法通过配置放行 `faccessat2`

2. **无法修改 Go 标准库**
   - `os/exec.LookPath` 是标准库函数
   - 不能 patch 或 hook

3. **可行的绕过方案**
   - 使用 `os.Stat`（底层调用 `fstatat`/`statx`，被允许）
   - 手动查找 binary 路径
   - 传入绝对路径给 `exec.Command`（跳过 lookPath）

### 实现细节

```go
// src/executil/safe_command.go
func SafeCommand(name string, args ...string) *exec.Cmd {
    // 如果已有路径分隔符，直接用（跳过 lookPath）
    if filepath.Base(name) != name {
        return exec.Command(name, args...)
    }
    
    // 在已知路径中查找（用 os.Stat，安全）
    knownPrefixes := []string{
        "/data/data/com.termux/files/usr/bin/",  // Termux
        "/system/bin/",                          // Android
        "/usr/bin/",                             // Linux
    }
    
    for _, prefix := range knownPrefixes {
        full := prefix + name
        if fi, err := os.Stat(full); err == nil && !fi.IsDir() {
            return exec.Command(full, args...)  // 绝对路径，跳过 lookPath
        }
    }
    
    // 兜底：交给 os/exec 处理
    return exec.Command(name, args...)
}
```

### 权衡

**放弃的东西**:
- 代码简洁性（每个 exec.Command 都要换成 SafeCommand）

**换取的东西**:
- OPC 能在 Termux 上运行
- 兼容 Android 设备（平板、手机）

### 教训

- **不要假设所有 Linux 都一样**
- Android 的 seccomp 策略比标准 Linux 严格
- 在真实设备上测试，不要只在 ECS 上测

---

## ADR-010: 刻意不做的功能

**状态**: ✅ 已采纳  
**决策者**: 项目创始人  
**日期**: 持续更新

### 列表

| 功能 | 不做的原因 |
|------|-----------|
| **Docker/K8s 集成** | 增加部署复杂度，当前规模不需要 |
| **GPU 驱动管理** | 需要 CUDA 专业知识，超出项目范围 |
| **多租户** | 当前是个人/小团队使用，不需要隔离 |
| **计费系统** | 不是 SaaS 产品 |
| **可视化编排界面** | 开发成本高，CLI 足够 |
| **分布式事务** | 任务短小，失败重试即可 |
| **实时流处理** | 不是数据处理平台 |
| **模型训练** | 只做推理调用，不做训练 |

### 理由

1. **YAGNI (You Aren't Gonna Need It)**
   - 不为假设的未来需求写代码
   - 当前用户（我自己）不需要这些功能

2. **复杂度控制**
   - 每多一个功能，维护成本指数增长
   - 1 人团队无法维护 10 个功能

3. **聚焦核心价值**
   - OPC 的核心: 分布式任务执行 + AI Agent
   - 其他功能可以集成第三方工具

---

## ADR-011: 已知局限和技术债

**状态**: ⚠️ 待处理  
**决策者**: 项目创始人  
**日期**: 持续更新

### 技术债清单

| ID | 描述 | 优先级 | 影响 |
|----|------|--------|------|
| TD-001 | Gateway 崩溃后任务丢失 | P2 | 中等 |
| TD-002 | 没有任务持久化 | P2 | 中等 |
| TD-003 | Agent 记忆无 semantic search | P3 | 低 |
| TD-004 | 单点故障（Gateway） | P2 | 中等 |
| TD-005 | 没有自动化测试 CI | P3 | 低 |
| TD-006 | 文档不完整 | P3 | 低 |
| TD-007 | 没有性能基准测试 | P3 | 低 |

### 详细说明

#### TD-001: Gateway 崩溃后任务丢失

**问题**: 任务存在内存队列中，Gateway 崩溃后队列清空。

**影响**: 用户需要重新提交未处理的任务。

**临时方案**: Worker 轮询时记录已认领的任务，重启后可以继续执行。

**彻底方案**: 引入 SQLite/WAL 持久化任务队列。

**优先级**: P2（当前任务量小，影响可控）

#### TD-002: 没有任务持久化

**问题**: 同 TD-001，任务不持久化。

**影响**: 无法审计历史任务。

**彻底方案**: 任务完成后写入 SQLite/PostgreSQL。

**优先级**: P2

#### TD-004: 单点故障（Gateway）

**问题**: 只有 1 个 Gateway，挂了整个系统不可用。

**影响**: 所有 Worker 无法接收新任务。

**临时方案**: 手动重启 Gateway。

**彻底方案**: 
- 主备 Gateway（leader election）
- 多 Gateway + 共享状态（需要引入分布式存储）

**优先级**: P2（当前是个人使用，可接受短暂停机）

---

## ADR-012: 未来架构演进方向

**状态**: 🔮 规划中  
**决策者**: 项目创始人  
**日期**: 2026-06

### 短期 (1-3 个月)

1. **任务持久化**
   - SQLite 存储已完成任务
   - 支持历史查询和审计

2. **Agent 协作**
   - 多 Agent 间的任务传递
   - 共享记忆池

3. **监控仪表盘**
   - Web UI 实时显示节点状态
   - 任务执行可视化

### 中期 (3-6 个月)

1. **多 Gateway 高可用**
   - Raft 协议选主
   - 任务自动 failover

2. **插件系统**
   - Worker 能力插件化
   - 第三方工具集成

3. **GPU 推理集成**
   - Worker 本地加载模型
   - 减少外部 API 依赖

### 长期 (6-12 个月)

1. **边缘计算**
   - 更多 Android 设备接入
   - 低功耗优化

2. **联邦学习**
   - 多节点协作训练模型
   - 数据不出本地

---

## 总结

OPC 是一个**务实的轻量级分布式系统**，核心设计原则：

1. **简单优先**: 能用 100 行代码解决的，不写 1000 行
2. **零外部依赖**: 不引入 K8s、消息队列、数据库
3. **内置 AI**: Agent 是系统的一等公民
4. **跨平台**: 一个 binary 跑所有系统
5. **聚焦核心**: 只做任务执行 + AI Agent

这些决策在当前规模（1 人团队、3-50 节点）下是合理的。如果规模增长 10 倍，需要重新评估 ADR-002（K8s）、ADR-003（消息队列）、ADR-005（微服务）。

---

**维护指南**: 每次重大架构变更时，新增一个 ADR-XXX 章节，记录决策和理由。半年后回来看，会感谢现在的自己。
