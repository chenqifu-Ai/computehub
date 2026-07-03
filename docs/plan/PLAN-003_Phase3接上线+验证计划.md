# PLAN-003: Phase 3 接上线 + 验证 + 后续推进计划

**制定**: 2026-07-02 06:35 | **制定人**: 小智 | **状态**: 待老大审批

---

## 1️⃣ 当前状态（刚完成的动作）

**Phase 3 初始化 bug 已修复** — `gateway.go` 加了一行 `SetPhase3()`，上线验证通过：

```
PUT  /api/v1/galaxy/phase3/stats          → ✅ success:true (4引擎全初始化)
PUT  /api/v1/galaxy/phase3/self-learning   → ✅
PUT  /api/v1/galaxy/phase3/innovation      → ✅
POST /api/v1/galaxy/phase3/cross-domain    → ✅ 路由已注册
POST /api/v1/galaxy/phase3/delegate        → ✅ 路由已注册
```

**目前 4 个引擎处于"空转就绪"状态** — 没任务流过所以统计全 0：
| 引擎 | 代码行 | 工作方式 | 当前 |
|------|--------|---------|------|
| SelfLearning | 205 行 | 每5个任务自动反思+知识蒸馏 | 空闲 |
| Innovation | 205 行 | 每10个任务探索一次知识盲区 | 空闲 |
| CrossDomain | 210 行 | 按需调用 — 跨专家任务分解 | 空闲 |
| SelfOrg | 370 行 | 按需调用 — 角色分配+同行评审+自动委派 | 空闲 |

---

## 2️⃣ 要验证的 4 件事（必须在第3步"跑任务"之前确认）

### 验证 A: SelfLearning → 知识提取 → Gateway 共享层  ← 主链路

Agent 跑任务 → `OnTaskCompleted()` → `SelfLearning.extractLesson()` → 写入 `memory.SaveKnowledge()` → 应该自动同步到 Gateway `ClusterMemory`

```
Agent Task → Phase3.OnTaskCompleted → distillKnowledge → SaveKnowledge → Gateway ClusterMemory
                                                    ↓
                                              (Verify with API)
```

**验证方法**: 执行一个任务 → 查 `/api/v1/galaxy/phase3/self-learning` 看 `knowledge_count` 是否增长 → 查 `/api/v1/knowledge/query` 看新知识是否到了 Gateway

### 验证 B: Innovation → 自动探索 → 知识盲区发现

Agent 跑 10 个任务 → Innovation 自动触发 `explore()` → 找知识盲区 → 设计实验 → 执行→ 记录发现

**验证方法**: 查 `/api/v1/galaxy/phase3/innovation` 看 `exploration_count` 和 `discovery_count`

### 验证 C: CrossDomain → 跨专家协作

POST 到 `/api/v1/galaxy/phase3/cross-domain` 带任务 → 调用 DecomposeTask → 分配 Expert

**验证方法**: 手动发请求看看返回

### 验证 D: SelfOrg → 同行评审

POST 到 `/api/v1/galaxy/phase3/delegate` 带任务 → 自动委派 + 同行评审

**验证方法**: 手动发请求看返回 JSON

---

## 3️⃣ 行动步骤

### Step 1: 环境就绪 ✅ Done
- 编译新 binary ✅
- 重启 Gateway ✅
- Phase 3 API 全部响应 200 ✅

### Step 2: 快速功能验证（手工 API 直调用 5 分钟）

| 序号 | 操作 | 预期 | 优先级 |
|------|------|------|--------|
| 2.1 | GET `/api/v1/galaxy/phase3/stats` | 4引擎全0初始值 | 🔴 必须 |
| 2.2 | POST 一个 task 到 Phase3 | 知识计数+1 | 🔴 必须 |
| 2.3 | POST `/api/v1/galaxy/phase3/cross-domain` | 返回任务分解 | 🟡 看结果 |
| 2.4 | POST `/api/v1/galaxy/phase3/delegate` | 返回委派方案 | 🟡 看结果 |
| 2.5 | GET `/api/v1/galaxy/phase3/innovation` | 探索统计 | 🟡 看结果 |

### Step 3: 跑真实任务（让引擎积累数据）

用 `exec_shell` 或 `manage_openclaw` 工具跑 5-10 个真实任务，观察引擎自学习：
- 跑后查 `self-learning` 统计
- 跑后查 `innovation` 统计
- 查知识库是否有新知识

### Step 4: 记录结果 + 下一步

确认链路通了以后，写入 GALAXY-PLAN.md 的 Phase 3 表格项，更新为 ✅ 已交付

---

## 4️⃣ 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| SelfLearning 调 LLM 可能超时 | 低 | 知识提取失败 | 超时设为 30s，失败静默 |
| Innovation 探索消耗 token | 中 | 额外 LLM 调用 | 每 10 次任务才触发一次 |
| SaveKnowledge → Gateway 同步失败 | 低 | 知识写本地但不同步到集群 | 检查知识同步回调注册 |
| Gateway 重启后 Phase 3 归零 | 中 | 统计丢失 | 统计是内存态，重启会归零，这是预期行为 |

---

## 5️⃣ 下一步（通过验证后）

1. 更新 GALAXY-PLAN.md 为 v2.1，将 Phase 3 表格全标 ✅
2. 发个 commit + tag: `docs: Phase 3 全部引擎上线验证通过`
3. 如果验证发现 bug，立即修复再跑

---

**行动计划**: 
- [ ] 老大审批 →
- [ ] 执行 Step 2 快速验证 →
- [ ] 执行 Step 3 跑任务 →
- [ ] 输出验证结果 →
- [ ] 更新文档 + commit

---

**签字**: _______________ (老大)     **日期**: 2026-07-02