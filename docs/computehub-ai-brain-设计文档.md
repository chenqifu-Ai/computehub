# ComputeHub AI 大脑 — 设计规划文档

> **版次**: v0.1 | **日期**: 2026-05-26 | **状态**: 设计阶段

---

## 1. 设计目标

### 1.1 一句话

> 在不引入 npm/TypeScript 依赖的前提下，把 OpenClaw 的 AI 思维循环（Agent Loop）移植到 ComputeHub 的 Go 二进制中。

### 1.2 约束条件

| 约束 | 说明 |
|------|------|
| ❌ **不引入新语言** | 只用 Go，不用 TypeScript/Python |
| ❌ **不引入 npm 生态** | 零外部 Go 依赖（除标准库和现有 go.mod 中的依赖） |
| ✅ **保持单文件编译** | `go build` 还是只输出一个 computehub 二进制 |
| ✅ **复用现有代码** | composer/client.go（LLM调用）、kernel/actions.go（任务类型）、workercmd（Worker交互） |
| ✅ **渐进落地** | 第一层 Day1 可用，第二层 Day3，第三层 Day7 |

---

## 2. 架构概览

### 2.1 整体结构

```
┌──────────────────────────────────────────────────────────────────┐
│                     ComputeHub Gateway                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │          Agent Core（新: src/agent/）                   │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │     │
│  │  │  Brain    │  │ Planner  │  │ Executor │             │     │
│  │  │ (循环)   │  │ (计划)   │  │ (执行)   │             │     │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘             │     │
│  │       │              │              │                    │     │
│  │       └──────────────┴──────────────┘                    │     │
│  │                        │                                 │     │
│  │              ┌─────────▼──────────┐                      │     │
│  │              │  Tool Registry     │                      │     │
│  │              │  (工具注册表)       │                      │     │
│  │              └─────────┬──────────┘                      │     │
│  └────────────────────────┼─────────────────────────────────┘     │
│                           │                                       │
│  ┌────────────────────────▼─────────────────────────────────┐     │
│  │              现有组件 (复用)                               │     │
│  │  ┌──────────────┐  ┌──────────┐  ┌──────────────────┐    │     │
│  │  │ LLM Client   │  │ Kernel   │  │ NodeMgr          │    │     │
│  │  │ composer/    │  │ scheduler│  │ + Worker集群     │    │     │
│  │  │ client.go    │  │          │  │                  │    │     │
│  │  └──────────────┘  └──────────┘  └──────────────────┘    │     │
│  └──────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 三层的定位

| 层 | 名称 | 定位 | 类比 OpenClaw |
|:--:|------|------|:-------------:|
| 🟢 **第一层** | Composer 接入 | Gateway 自动拆解任务 | OpenClaw 的 TaskComposer（已实现但未启用） |
| 🟡 **第二层** | Agent 端点 | 自然语言交互能力 | `runEmbeddedPiAgent()` 的简约版 |
| 🔴 **第三层** | Brain 循环 | 自主决策 + 心跳+记忆+技能 | OpenClaw 的完整 Agent 系统 |

**核心原则**: 每一层都是上一层的超集，可独立上线。

---

## 3. 第一层 🟢 Composer 接入（Day 1）

### 3.1 目标

让 Gateway 提交任务时自动用大模型拆解成子任务，并行分发给 Worker，收结果后合并。

### 3.2 现有资产（零新增代码）

```
src/composer/
├── client.go      → ✅ LLM API 客户端 (143行, 纯 HTTP, 零外部依赖)
│                    ✅ 已适配 NewAPI content→reasoning fallback
│                    ✅ 默认 URL = https://ai.zhangtuokeji.top:9090
│                    ✅ 支持 Chat() + CallWithPrompt()
│
├── composer.go    → ✅ TaskComposer (分解→分发→合并, ~500行)
│                    ✅ Decomposer 接口 + LLMDecomposer 实现
│                    ✅ Compositor 接口 + LLMCompositor 实现
│                    ✅ DispatchEngine (并行分发 + 重试 + 指数退避)
│                    ✅ Run() 完整编排流程
│
└── composer_test.go → ✅ 有测试
```

### 3.3 改动清单

```diff
// 文件1: config.json
- "api_url": "http://localhost:11434/v1",
- "api_key": "",
- "model": "deepseek-v4-flash",
+ "api_url": "https://ai.zhangtuokeji.top:9090/v1",
+ "api_key": "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl",
+ "model": "qwen3.6-35b-common",
- "execute_models": ["deepseek-v4-flash", "qwen3.6-35b", "llama3.1:8b"],
+ "execute_models": ["qwen3.6-35b-common"],

// 文件2: src/gateway/gateway.go  handleTaskSubmit()
  if g.Composer != nil {
-     // In a real scenario, complex tasks would be decomposed here
-     // For now, we just submit the task as-is
+     // 简单命令直接调度，复杂命令走 Composer
+     if isComplexTask(task.Command) {
+         go g.composerDecomposeAndDispatch(task)
+     }
  }

// 文件3: src/gateway/gateway.go  新增函数
+ func (g *OpcGateway) composerDecomposeAndDispatch(task *kernel.TaskSubmit) {
+     // 调用 Composer.Run 拆解任务 → 派发子任务 → 收集结果
+ }

// 文件4: src/gateway/gateway.go  新增辅助函数
+ func isComplexTask(cmd string) bool { ... }
```

### 3.4 简单 vs 复杂命令判断

```
简单命令（直接调度）:     复杂命令（走 Composer）:
  ls /tmp                  分析这些服务器日志
  df -h                    帮我生成一份周报
  ping 8.8.8.8             对比这两个文件
  nvidia-smi                写一个脚本定期备份数据库
  单行 shell 命令          自然语言指令
```

判断逻辑：如果命令不是有效 shell（含空格、自然语言特征）→ 走 Composer。

### 3.5 效果

```
用户 POST 复杂任务 → Gateway:
  1. 调 NewAPI(qwen3.6) 拆解成子任务
  2. 自动提交子任务到 Worker 集群并行执行
  3. 汇总结果，调 NewAPI 合并
  4. 返回最终回答
```

---

## 4. 第二层 🟡 Agent 端点（Day 2~4）

### 4.1 目标

新增端点 `/api/v1/agent/think`，接收自然语言指令，自主生成执行计划，驱动 Worker 执行。

### 4.2 新增代码

#### 4.2.1 `src/agent/agent.go` — Agent 主入口

```go
// Agent 处理自然语言请求
// 输入: 用户问题 + 上下文
// 流程: 思考 → 规划 → 执行 → 回答
type Agent struct {
    llm      *composer.LLMClient
    registry *ToolRegistry
    kernel   *kernel.ExtendedKernel
}

func (a *Agent) Think(ctx context.Context, req *AgentRequest) (*AgentResponse, error) {
    // 1. 构建系统提示（含可用工具列表、节点状态）
    // 2. 调用 LLM → 生成执行计划（JSON格式）
    // 3. 遍历计划步骤：
    //    - shell → 创建 TaskSubmit → 派发 Worker
    //    - text  → 直接 LLM 处理
    //    - code  → 创建 TaskSubmit
    // 4. 收集所有子结果
    // 5. 调 LLM 生成最终回答
}
```

#### 4.2.2 `src/agent/tools.go` — 工具注册表

```go
type Tool struct {
    Name        string
    Description string
    Parameters  JSONSchema
    Execute     func(ctx Context, args JSON) (string, error)
}

type ToolRegistry struct {
    tools map[string]Tool
}

// 注册 ComputeHub 专有工具
// - exec_shell: 在指定Worker执行shell命令
// - exec_llm:   直接调LLM做文本处理
// - node_status: 查询节点状态
// - task_list:   查询任务队列
// - gallery_list: 查询作品列表
```

工具注册模式参考 OpenClaw 的 `src/agents/tools/`，但极简化：每个工具是一个 Go struct，不是 npm 包。

#### 4.2.3 `src/agent/planner.go` — 计划生成

从 OpenClaw `run.ts` 的 Agent 循环中提取核心逻辑：

```go
// Planner 生成并管理执行计划
type Planner struct {
    llm *composer.LLMClient
}

// Plan 调大模型生成结构化执行计划
// 系统提示: 描述可用工具、节点现状、任务约束
// 输出: JSON 格式的步骤列表
func (p *Planner) Plan(ctx context.Context, task string, context *Context) ([]Step, error)

// Step 表示一个执行步骤
type Step struct {
    ID       int         // 步骤序号
    Type     string       // "shell" | "llm" | "code"
    Tool     string       // 使用的工具名
    Args     interface{}  // 参数
    Depends  []int        // 依赖的步骤ID
    Status   string       // "pending" | "running" | "done" | "failed"
    Result   string       // 执行结果
}
```

#### 4.2.4 `src/gateway/gateway.go` — 路由注册

新增:
```go
http.HandleFunc("/api/v1/agent/think", g.handleAgentThink)
```

### 4.3 Agent 端点请求/响应格式

```
POST /api/v1/agent/think
{
  "task": "分析 /var/log 下最近的错误日志，生成摘要报告，发送到我的邮箱",
  "session_id": "chat-001",
  "context": {
    "nodes": ["worker-sz-01", "worker-bj-01"],
    "region": "cn-east"
  }
}
```

响应（流式或一次性）:
```json
{
  "session_id": "chat-001",
  "thought": "需要先收集日志，然后分析，最后写报告并发送...",
  "plan": [
    {"step": 1, "type": "shell", "tool": "exec_shell", "on": "worker-sz-01",
     "command": "grep -i error /var/log/syslog | tail -100"},
    {"step": 2, "type": "llm", "tool": "exec_llm",
     "input": "分析以下日志中的错误模式...", "depends": [1]},
    {"step": 3, "type": "shell", "tool": "exec_shell", "on": "worker-bj-01",
     "command": "echo '报告内容' | mail -s '日志摘要' 19525456@qq.com",
     "depends": [2]}
  ],
  "result": "分析完成，摘要已发送到邮箱。\n发现 3 个关键错误..."
}
```

### 4.4 与 OpenClaw 的对应关系

| OpenClaw 概念 | ComputeHub 实现 | 简化程度 |
|:-------------:|:---------------:|:--------:|
| `runEmbeddedPiAgent()` 主循环 | `Agent.Think()` 循环 | 简化版 |
| `runEmbeddedAttempt()` 单次执行 | `Planner.plan()` + 逐步执行 | 大幅简化 |
| `buildEmbeddedRunPayloads()` 消息构建 | `buildSystemPrompt()` + 组装请求 | 简化 |
| `tools/` 目录（~20个工具） | `ToolRegistry` + 5个工具 | 极简化 |
| `model.ts` 模型适配 | `composer/client.go` 已有 | 复用 |
| `skills/` 技能系统 | Go interface 注册 | 简化 |
| `system-prompt.ts` 提示构建 | 模板字符串 | 极简化 |
| `compaction.ts` 上下文压缩 | 暂不实现 | 跳过 |
| auth-profiles + failover | 暂不实现 | 跳过 |

---

## 5. 第三层 🔴 Brain 循环（Day 5~7）

### 5.1 目标

让 Gateway 像 OpenClaw 一样能"自主醒来"，主动决策该做什么。

### 5.2 新增代码

#### 5.2.1 `src/agent/brain.go` — 后台循环

```go
type Brain struct {
    agent      *Agent
    memory     *Memory
    skills     *SkillRegistry
    interval   time.Duration  // 默认 30s
}

func (b *Brain) Start() {
    // 1. 启动时执行一次 boot 检查
    // 2. 每 30s 触发一次 heartbeat 决策
    //    - 检查节点健康、任务队列
    //    - 调用 LLM 判断"现在需要做什么"
    //    - 如果有需要自动完成的事情 → 创建并执行任务
    // 3. 主动汇报（定期发邮件）
    go b.boot()
    go b.heartbeatLoop()
}
```

参考 OpenClaw 的 `gateway/boot.ts` + heartbeat 机制，但用 Go 的 `time.Ticker` 实现。

#### 5.2.2 `src/agent/memory.go` — 对话记忆

```go
type Memory struct {
    storePath string  // 文件路径 e.g. /tmp/computehub-memory.json
}

// Store 存储对话/任务上下文
func (m *Memory) Store(sessionID string, entry MemoryEntry) error

// Recall 检索相关记忆
func (m *Memory) Recall(query string, limit int) ([]MemoryEntry, error)

// Summarize 压缩长对话
func (m *Memory) Summarize(sessionID string) (string, error)
```

简化版：文件存储 JSON，不依赖 Git。需要时再升级。

#### 5.2.3 `src/agent/skills.go` — 技能系统

```go
type Skill struct {
    Name        string `json:"name"`
    Description string `json:"description"`
    Trigger     string `json:"trigger"`   // LLM 判断触发关键词
    Action      string `json:"action"`    // 执行动作
    Params      map[string]interface{} `json:"params"`
}

// 技能从 JSON 文件注册（参考 OpenClaw 的 skill.md）
// {"skills": [{"name":"日志分析", "trigger":"分析日志", "action":"exec_shell", ...}]}
```

### 5.3 Brain 循环流程图

```
┌──────────────────────────────────────┐
│         Brain 启动                    │
│         ┌─────────────────┐          │
│         │ boot()          │          │
│         │ 读 BOOT.md      │          │
│         │ 执行启动任务     │          │
│         └────────┬────────┘          │
│                  │                    │
│         ┌────────▼────────┐          │
│         │ heartbeatLoop() │          │
│         │ 每 30s 触发     │          │
│         └────────┬────────┘          │
│                  │                    │
│         ┌────────▼────────┐          │
│         │ 检查节点状态     │          │
│         │ 检查任务队列     │          │
│         │ 检查 Gallery    │          │
│         └────────┬────────┘          │
│                  │                    │
│         ┌────────▼────────┐          │
│         │ LLM 判断:      │          │
│         │ "现在需要干什么?"│         │
│         └────────┬────────┘          │
│                  │                    │
│          ┌───────┴───────┐           │
│          ▼               ▼           │
│   需要做某事        不需要做事        │
│    │                     │           │
│    ▼                     ▼           │
│ 创建任务 → 执行      继续等待        │
└──────────────────────────────────────┘
```

---

## 6. 文件结构规划

### 6.1 新增目录

```
src/agent/                    ← 新增，Agent 系统根目录
├── agent.go                  # Agent 主入口 (Think 循环)
├── agent_test.go             # Agent 测试
├── tools.go                  # 工具注册表 (ToolRegistry)
├── tools_test.go             # 工具测试
├── planner.go                # 计划生成 (Planner)
├── planner_test.go           # 计划测试
├── brain.go                  # 自主循环 (Brain)
├── memory.go                 # 对话记忆
├── skills.go                 # 技能注册
└── README.md                 # Agent 系统说明
```

### 6.2 改动文件

```
src/gateway/gateway.go        → 注册 /api/v1/agent/think 端点
src/gatewaycmd/cmd.go         → Agent 初始化（Brain 启动）
config.json                   → api_url/api_key/model 指向 NewAPI
```

### 6.3 代码行数预估

| 文件 | 预估行数 | 备注 |
|------|:-------:|------|
| `agent/agent.go` | ~150 | Think 循环核心 |
| `agent/tools.go` | ~120 | 5个工具注册 + schema |
| `agent/planner.go` | ~200 | LLM 计划生成 + 执行 |
| `agent/brain.go` | ~100 | 心跳循环 |
| `agent/memory.go` | ~80 | 文件存储 |
| `agent/skills.go` | ~60 | JSON 注册 |
| 改动现有文件 | ~50 | gateway/cmd |

**新增总计: ~760 行 Go 代码**（对比 OpenClaw: 4,421 行 TypeScript + 几千个 npm 包）

---

## 7. 关键设计决策

### 7.1 为什么不用 `composer/composer.go` 的现有代码？

现有 Composer 的设计是 "大模型拆 → 小模型并行干 → 大模型汇总"，适用于单次任务。

而 Agent 需要的是 **交互式思维循环**：调 LLM → 得到一个行动 → 执行 → 结果反馈 → 再次调 LLM。

所以：
- **复用** `composer/client.go`（LLM API 调用）
- **不复用** `composer/composer.go` 的编排逻辑（太死板）
- **新写** `agent/` 目录的 think→plan→act→loop

### 7.2 与现有 Worker 的关系

Agent 不直接执行命令，而是：
```
Agent → 创建 TaskSubmit → 走现有调度系统 → Worker 执行 → 结果回来 → Agent 继续
```

这样 Agent 只是一个"聪明的人"，而 Worker 还是"能干的手"。完全解耦。

### 7.3 安全边界

| 安全点 | 措施 |
|--------|------|
| Agent 不能直接执行 | 只创建 TaskSubmit，走 kernel 调度 |
| 命令白名单 | 工具注册时定义允许的参数 |
| 敏感操作确认 | 删除/重装等操作需要用户确认 |
| API Key 不泄露 | 只在 server 端调用 |

---

## 8. 风险与缓解

| 风险 | 级别 | 缓解 |
|:----:|:----:|------|
| LLM 返回格式不符合预期 | 🟢 | 重试 + fallback 为直接调度 |
| NewAPI 超时/不可用 | 🟡 | Go 标准 http.Client 超时 30s |
| Agent 循环死循环 | 🟡 | max_iterations 上限（默认 10） |
| 记忆文件膨胀 | 🟢 | 限制单条 10KB，总文件 1MB |
| Worker 安全（无 TLS） | 🔴 | 独立问题，不在此方案范围内 |

---

## 9. 实施路线

```
Day 1 ──── 第一层: config 指向 NewAPI + 取消 Composer 注释
               ↓ 编译 → deploy → 验证
Day 2-3 ── 第二层: agent.go + tools.go + planner.go
               ↓ 编译 → deploy → 测试 agent/think
Day 4-5 ── 第二层完善: 路由注册 + 流式响应 + 错误处理
               ↓ 接入 TUI 展示
Day 6-7 ── 第三层: brain.go + memory.go + skills.go
               ↓ Brain 自主运行
```

### 里程碑验收标准

| 层 | 验收标准 |
|:--:|----------|
| 🟢 | `curl POST .../api/v1/tasks/submit -d '{"command":"帮我分析日志"}'` → 自动拆解+分配+汇总 |
| 🟡 | `curl POST .../api/v1/agent/think -d '{"task":"..."}'` → 返回结构化回答 |
| 🔴 | Gateway 每 30s 自动检查节点状态，发现异常主动汇报 |

---

## 10. 附录：与 OpenClaw 的代码对应表

| OpenClaw src/ | 行数 | 依赖 | ComputeHub 方案 |
|:-------------:|:----:|:----:|:---------------:|
| `pi-embedded-runner/run.ts` | 1,608 | 几十个 npm 包 | `agent/agent.go` ~150行 |
| `pi-embedded-runner/run/attempt.ts` | 2,813 | 几十个 npm 包 + `pi-coding-agent` | 不直接移植，提取设计 |
| `pi-embedded-runner/run/payloads.ts` | ~300 | `pi-ai` | `agent/planner.go` + composer |
| `pi-embedded-runner/model.ts` | ~300 | 模型发现 + 配置 | composer/client.go ✅ 已有 |
| `tools/ (20个工具)` | ~2000 | 各不相同 | `agent/tools.go` ~120行 (5个) |
| `skills/ (技能系统)` | ~800 | 文件解析 + 注入 | `agent/skills.go` ~60行 |
| `memory/` | ~400 | git + fs | `agent/memory.go` ~80行 |
| `gateway/boot.ts` | ~200 | fs + session | `agent/brain.go` boot() ~50行 |
| cron 系统 | ~500 | node-cron | Go `time.Ticker` 原生 |
| **合计参考** | **~9,000行** | **数百个 npm 包** | **~760行 Go 代码, 零外部依赖** |

---

> **结论**: 以 ~760 行纯 Go 代码（无 npm、无 TypeScript、无外部依赖），复现 OpenClaw AI Agent 核心能力的 ~80%。保持原 Go 单文件编译、零部署成本。
