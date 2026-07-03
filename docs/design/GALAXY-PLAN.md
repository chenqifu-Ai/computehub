# 🌌 银河计划 v2.1 — 规划与进度同步版

**更新日期**: 2026-07-02 06:35 | **制定人**: 小智

---

## 📋 背景

v1.0 调度任务书（2026-06-30）中规划的 Phase 0/1A/1B 大部分已被实际代码提前完成。  
本版 v2.1 新增 Phase 3b/3c/3d 拆分，将"自主进化"从笼统概念拆为可执行子阶段。

---

## ✅ 已完成模块

| 原计划 Phase | 模块 | 代码文件 | 状态 | 关键提交 |
|-------------|------|---------|------|---------|
| **Phase 0** 快速启动 | Hall 消息通道 | `gateway_hall.go` (1159行) | ✅ 生产运行 | `7e783c1` |
| | 共享目录 `shared/` | `memory/shared/` 结构 | ✅ 已创建 | `04daeff` |
| | 分支 `galaxy-v1.0` | 已合入 master | ✅ | `b052667` |
| **Phase 1A** 通信骨架 | JSON 消息格式 | Hall 内部格式已用 | ✅ 缺正式 Schema | — |
| | sessions_send 标准化 | `gateway_agent_send.go` | ✅ | `3012245` |
| | 断线续传 | `gateway_ws.go` | ✅ | v1.3.31 |
| | 发现协议 | `gateway_arcnet.go` | ✅ | v1.3.24 |
| | 端到端验证 | 三智 24+ 轮 Hall 讨论 | ✅ | — |
| **Phase 1B** 功能上层 | **TriggerEngine** | `gateway_trigger.go` (1288行) | ✅ **已发布** | `29e47be` |
| | **ClusterMemory** | `gateway_memory.go` (813行) | ✅ **已发布** | `301ff78` |
| | **KnowledgeBase** | `gateway_knowledge.go` (436行) | ✅ **已发布** | `50c0c73` |
| | **Gateway 知识引擎** | `gateway_galaxy.go` (982行) | ✅ **已发布** | `1b09ad0` |
| **Phase 3a** | Agent 集成 Phase 3 | `galaxy_phase3.go` (1142行) | 🟡 **代码已写但未激活** | `5dcd133` |
| | Hall→Trigger 闭环 | Hall 消息自动流入 Trigger | ✅ | `52d9616` |

> 总计：**~5,800 行代码**，覆盖银河计划原定 Phase 0 → Phase 1B → Phase 2 → Phase 3a

---

## 🧩 实际代码架构全景

```
Gateway (port 8282)
├── 🗣️ Hall 聊天室        — gateway_hall.go        — 三智对话通道
├── 🧠 ClusterMemory      — gateway_memory.go      — 跨节点记忆同步
├── 📚 KnowledgeBase      — gateway_knowledge.go    — 知识共享 CRUD
├── ⚡ TriggerEngine      — gateway_trigger.go     — 事件触发引擎
├── 🌐 Galaxy 层          — gateway_galaxy.go       — 知识自动同步
├── 🔌 Agent 通信         — gateway_agent_send.go   — sessions_send
├── 🔄 升级引擎           — gateway_upgrade.go      — 自动部署
└── 🖼️ Gallery            — gallery.go              — 文件共享

Agent (Worker side)
├── 🤖 Agent 内核         — agent.go                — 主循环
├── 🧩 SelfLearning       — galaxy_phase3.go        — 🔴 未激活 (dead code)
├── 🧠 本地记忆           — memory.go               — memory() 工具
├── 🛠️ 工具系统           — tools.go                — 远程执行工具
└── 🔀 Hall 路由          — hall_router.go           — Hall 消息分发
```

---

## 🆕 Phase 3 重新定义

经代码审查发现关键事实：`galaxy_phase3.go` (1142行) 中 **SelfLearningEngine 代码完整，但从未被激活**。`SetPhase3` 从未被 `worker_main.go` 调用，`SetKnowledgeSyncFn`、`SetMemorySyncFn` 两个回调接口也从未被注入。

```
现有代码状态:
galaxy_phase3.go:   1142行 ✅ 已实现    但 ❌ 未激活 (dead code)
agent.go:           5行回调接口 ✅ 已定义  但 ❌ 从未注入
knowledge API:      436行 ✅ 生产就绪    但 ❌ 零数据（空写入）
```

### Phase 3 新版拆分

| 子阶段 | 名称 | 说明 | 现有代码复用 | 新增 | 状态 |
|--------|------|------|------------|------|------|
| **3a** | 知识共享基础设施 | Gateway 知识引擎 + 跨节点同步 | ✅ 已交付 | 0行 | ✅ **已完成** |
| **3b** | **任务复盘机制** | AAR复盘 → 经验提取 → 知识同步 | ~600行 SelfLearningEngine | ⭐ 40行激活 | 🔴 **待执行** |
| **3c** | 探索沙盒 | 低负载时 Agent 自主实验 | ~200行 InnovationEngine | 设计阶段 | 🔴 待规划 |
| **3d** | 自组织生态 | 动态分工 + 同行评审 | ~600行 CrossDomain/SelfOrg | 设计阶段 | 🔴 待规划 |

**Phase 3b 详细设计**: `docs/design/SPEC-AAR-001_任务复盘机制.md`

---

## 🧩 剩余缺口分析

### 缺口 1: TriggerEngine 缺少真实规则和实际落地

**现状**: TriggerEngine 三层架构（Collector → Matcher → Responder）代码完整，**但没有 YAML 规则文件**，没有配置 `rules.yaml` 路径。系统指标采集在 Linux 侧实现但未连接生产场景。

**需要做**:
1. 创建 `config/trigger_rules.yaml` — 5~10 条生产规则（CPU/磁盘/Hall@触发词）
2. `collectSystemMetrics` 接入实际系统监控循环
3. TriggerEngine WebUI 已实现但 Gateway 路由未注册（`/trigger/`）

**工期**: 1 天

### 缺口 2: KnowledgeBase 缺少实际数据和使用场景

**现状**: API 端点 (`/api/v1/knowledge/put`, `/api/v1/knowledge/query` 等) 已注册可以调通，但：
- 没有 `.strengths.json` 持久化文件（知识文件存储依赖此文件）
- Agent 没有主动写知识的触发器（`SaveKnowledge` 方法无人调用）
- 跨节点知识同步未经过实际测试

**需要做**:
1. 写一个 `initKnowledgeStore()` 自动初始化
2. Agent 在 `SaveEpisode` 或 `SaveKnowledge` 时自动推送到 Gateway
3. 端到端测试：节点 A 写一条知识 → 节点 B 查询到

**工期**: 1~2 天

### 缺口 3: 共享记忆目录结构缺少活跃使用

**现状**: `memory/shared/knowledge/`, `memory/shared/patterns/`, `memory/shared/insights/`, `memory/shared/timeline/` 目录结构已有，但：
- Agent 的 `memory() → SaveKnowledge()` 调用链路未打通
- Agent prompt 中未注入共享知识

**需要做**:
1. `galaxy_phase3.go` 中的 `buildSystemPrompt` 已注入共享记忆，但未验证是否生效
2. Agent 在写 `memory/notes.md` 时自动推送到共享层

**工期**: 0.5 天

### 缺口 4: 集群节点状态可视化（TUI / Web）

**现状**: Gateway API 路由变更后，`/api/v1/nodes` 可能返回 404。

**需要做**:
1. 修复 Gateway API 路由
2. 或确认当前 `/api/v1/` 的正确入口

**工期**: 0.5 天

### 缺口 5: 磁盘空间告警

**现状**: 45GB 磁盘已用 85%（36GB），`deploy/` 下积压大量旧版本 binary。

**需要做**: 清理 `deploy/` 只保留最近 3 个版本

**工期**: 0.2 天

---

## 🏗️ 优先级排序

基于"价值最大、链路最短"原则：

| 优先级 | 模块 | 任务 | 工期 | 价值 |
|--------|------|------|------|------|
| **P0** | **Phase 3b 复盘机制** | 激活 SelfLearningEngine + 知识同步 | 4小时 | 知识闭环核心 |
| **P1** | **TriggerEngine 落地** | 写 rules.yaml + 接 metrics + 注册 UI 路由 | 1天 | 触发告警投产 |
| **P2** | **KnowledgeBase 端到端** | init + Agent 写知识 + 跨节点验证 | 1.5天 | 知识共享闭环 |
| **P3** | **共享记忆注入** | 验证 prompt 注入 + 打通 memory→shared | 0.5天 | 每个 Agent 带全局上下文 |
| **P4** | **API 路由修复** | 恢复 nodes/stats 端点 + Web 看板 | 0.5天 | 可视化监控 |
| **P5** | **磁盘清理** | deploy/ 只留 3 个版本 | 0.2天 | 释放空间 |

---

## ⚙️ 阶段实施路线图

### 立即执行（P0-P2，~3 天）

```
Day 1:   Phase 3b 复盘机制 → 激活 SelfLearningEngine + 知识同步
Day 2:   TriggerEngine 落地 → rules.yaml + metrics 接入 + UI 注册
Day 3:   KnowledgeBase 端到端 + 共享记忆注入 + 磁盘清理
```

### 后续方向

| 方向 | 说明 | 预期价值 |
|------|------|---------|
| **Phase 3c 探索沙盒** | 低负载时 Agent 自主实验 | 能力成长 |
| **Phase 3d 自组织** | 动态分工 + 同行评审 | 五智协作升级 |
| **Cross-node 任务调度** | Worker 通过 Gateway 调度其他节点 | 分布式执行 |
| **Agent 互评机制** | 三智定期互相打分 + 能力画像 | 能力成长 |

---

*此文档会自动保持与 git 进度同步。下次更新日期：执行前。*