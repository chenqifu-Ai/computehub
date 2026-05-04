# 🚀 全量代码扫描与执行链路审计报告
**扫描时间**: 2026-04-20 08:45
**扫描范围**: `/root/.openclaw/workspace/openclaw-project` 及 `/root/.openclaw/workspace/framework`

## 1. 核心架构拓扑 (Topological Map)

经过全量文件扫描，系统呈现出明显的 **"双轨制"** 架构：

### 轨 A: TypeScript/Node.js 核心 (OpenClaw Project)
这是系统的“神经中枢”和“外壳”，负责所有低级调度和协议对接。
- **入口**: `/src/entry.ts` $\rightarrow$ `/src/daemon` (服务化) $\rightarrow$ `/src/gateway` (协议转换)
- **调度**: `/src/auto-reply/reply` (响应逻辑) $\rightarrow$ `/src/agents/pi-embedded-runner` (模型驱动运行)
- **工具链**: `/src/agents/tools` (工具定义) $\rightarrow$ `/src/agents/sandbox` (执行隔离)
- **内存/上下文**: `/src/context-engine` $\rightarrow$ `/packages/memory-host-sdk` (向量化存储)

### 轨 B: Python 智能体框架 (AI Agent Framework)
这是系统的“肌肉”和“执行手脚”，负责复杂任务的闭环实现。
- **核心引擎**: `/root/.openclaw/workspace/framework/ai_agent.py`
- **执行逻辑**: `Think` $\rightarrow$ `Code` $\rightarrow$ `Execute` $\rightarrow$ `Learn` (SOP 7步法在代码中的具体体现)
- **资产路径**: `/ai_agent/code` (临时代码) $\rightarrow$ `/ai_agent/results` (执行结果)

---

## 2. 链路审计分析 (Audit Analysis)

### ⚠️ 关键发现：逻辑断层与“伪执行”风险
在审计 `framework/ai_agent.py` 时，发现一个严重的 **实现漏洞**：

**漏洞点**: `think()` 和 `code()` 方法目前是 **硬编码模拟 (Mock)**。
- **代码证据**: 
  - `think()` 直接返回一个静态的 `thought` 字典。
  - `code()` 直接生成一个带有 `TODO` 的模板 Python 脚本。
- **后果**: 如果直接调用该类而不进行外部 LLM 注入，智能体将陷入 **“表演性执行”** —— 它看起来在思考、写代码、执行，但实际运行的是一个没有逻辑的空壳脚本。

### 🛠️ 执行路径真实流向
真实的执行链路应为：
`User Request` $\rightarrow$ `AutoReply (TS)` $\rightarrow$ `Agent Runner (TS)` $\rightarrow$ `Shell Exec (Python Script)` $\rightarrow$ `AIAgent.run()` $\rightarrow$ `LLM API (External)` $\rightarrow$ `Dynamic Python Code` $\rightarrow$ `Subprocess Execution`.

---

## 3. 潜在风险点 (Red Flags)

1. **错误静默**: `/src/agents/pi-embedded-runner/run.ts` 中存在大量复杂的 `try-catch` 块，部分错误被转化为 `fallback` 而非直接上报，可能掩盖链路中断。
2. **权限边界**: `pi-tools.ts` 的 `workspace-root-guard` 虽然存在，但在 `sandbox` 模式下，如果挂载点配置错误，仍存在越权风险。
3. **并发瓶颈**: `subagent-registry` 的状态同步依赖于文件锁/内存快照，在高频并发调用时可能出现竞态条件。

---

## 4. 后续加速计划 (Next Steps)

- [ ] **修复 AIAgent 模拟漏洞**: 将 `ai_agent.py` 的 `think` 和 `code` 方法与真实 LLM API 绑定。
- [ ] **链路穿透测试**: 构造一个端到端的复杂任务，记录从 TS 层到 Python 层的完整时间戳，审计是否存在“跳步”执行。
- [ ] **冗余清理**: 识别并标记 `/src/agents/tools` 中不再使用的遗留工具。
