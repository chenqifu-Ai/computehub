# SPEC-AAR-001 — 任务复盘机制（After-Action Review）

**版本**: v1.0  
**日期**: 2026-07-02  
**制定人**: 小智  
**状态**: 待评审  
**关联**: GALAXY-PLAN.md Phase 3b / SPEC-TRIGGER-001 / SPEC-DMEM-001 / SPEC-GALAXY-003

---

## 📋 1. 问题陈述

### 1.1 现状痛点

| 维度 | 现状 | 问题 |
|------|------|------|
| Agent 执行任务 | 调用 LLM → 返回结果 → 完成 | **做完即忘**，不复盘不总结 |
| TriggerEngine | 监控 CPU/内存/Hall 消息 → 触发规则 | 监控了**系统**，没人监控**Agent行为** |
| KnowledgeBase | 知识 CRUD 端点全 | **没人写**，只有框架没有数据 |
| SelfLearningEngine | 代码完整(extractLesson/distill/reflect) | **没人激活**(SetPhase3 从未调用) |
| Agent.memorySyncFn | 定义了回调接口 | **没人连**(Worker 未注入) |

### 1.2 核心缺口

```
当前链路：
  任务执行 → Agent返回 → 结束  (❌ 无复盘)
  
期望链路：
  任务执行 → Agent返回 → 自动复盘 → 提取经验 → 写入KnowledgeBase → 广播同步
                                                          ↕
                                                  其他Agent可查可学
```

### 1.3 目标

> 让每次 Agent 执行任务都能自动生成复盘，经验自动沉淀到共享知识库，所有 Agent 可复用。

---

## 🧩 2. 架构设计

### 2.1 整体链路

```
┌─────────────────────────────────────────────────────────┐
│                    Worker 侧 (Agent)                     │
│                                                         │
│  任务完成                                                │
│     │                                                    │
│     ▼                                                    │
│  Agent.processTask()                                     │
│     │                                                    │
│     ├─→ 返回结果给用户                                    │
│     │                                                    │
│     └─→ Phase3.OnTaskCompleted()  ← 已接入，但 Phase3=null│
│               │                                           │
│               ▼                                          │
│         下一版: SelfLearningEngine 被激活                  │
│               │                                           │
│               ├─→ extractLesson() → SaveEpisode()        │
│               │       └→ 写到本地 GitMemory              │
│               │                                           │
│               ├─→ distillKnowledge() → SaveKnowledge()   │
│               │       └→ 写到本地 GitMemory               │
│               │       └→ 触发 knowledgeSyncFn            │
│               │             └→ HTTP POST Gateway知识库    │
│               │                                           │
│               └─→ reflect()  (每5次任务)                  │
│                     └→ LLM反思 → 保存到知识库             │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (POST /api/v1/knowledge/put)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Gateway 侧                             │
│                                                         │
│  POST /api/v1/knowledge/put                              │
│     │                                                    │
│     ▼                                                    │
│  KnowledgeStore.put()                                    │
│     │                                                    │
│     ├─→ 写入 data/cluster_memory.json                    │
│     ├─→ 写入 data/knowledge/lesson/ 文件                  │
│     └─→ (未来) 消息广播给所有在线 Worker                  │
│                                                         │
│  GET /api/v1/knowledge/query                             │
│     └─→ 其他Agent可以查询知识                             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 复盘触发时序

```
时间线
│
├─ [T+0s]   用户/系统提交任务到 Gateway
├─ [T+1s]   Gateway 分发任务到 Worker
├─ [T+2s]   Agent 执行 (LLM + 工具调用)
├─ [T+3s]   Agent.onTaskProcessed()  ← Phase3 回调
│              │
│              ├─ [T+3.1s] extractLesson()
│              │   ├─ 检查执行计划：哪些步骤成功/失败
│              │   ├─ 提取关键教训（成功技巧/失败原因）
│              │   └─ SaveEpisode → GitMemory commit
│              │
│              ├─ [T+3.2s] distillKnowledge()  (仅成功任务)
│              │   ├─ LLM 从执行结果中蒸馏可复用知识
│              │   ├─ SaveKnowledge → GitMemory commit
│              │   └─ knowledgeSyncFn → POST Gateway
│              │
│              └─ [T+3.3s] reflect()  (每5次任务)
│                  ├─ LLM 回顾近期表现
│                  ├─ 输出改进方向
│                  └─ SaveKnowledge("自我反思 #N", ...)
│
└─ [T+4s]   结果返回到用户
            （复盘完全不阻塞用户，goroutine 异步执行）
```

---

## 🔌 3. 实现方案

### 3.1 方案 A — 激活现有 SelfLearningEngine（推荐）

**改动量**: 最小  
**核心**: 在 Worker 启动时调用 `agent.SetPhase3()` 即可让现有 1100 行复盘代码生效。

#### 需要改动的代码

| 文件 | 改动 | 行数 |
|------|------|------|
| `src/workercmd/worker_main.go` | 创建 Phase3 并注入 Agent | ~20 行 |
| `src/workercmd/worker_agent.go` | 在Agent初始化后注入memorySyncFn/knowledgeSyncFn | ~20 行 |
| `src/agent/agent.go` | 确保 Phase3 在 onTaskProcessed 中被调用（已写好） | 0 行 |
| `src/gateway/gateway.go` | 知识库API端点注册（已注册） | 0 行 |

#### worker_main.go 改动示例

```go
// 在 initAgent() 或 main() 中
if agent != nil && memory != nil {
    // 1. 创建 Phase3 管理器
    phase3 := agent.NewGalaxyPhase3Manager(agent, expertRegistry, memory, llmClient)
    agent.SetPhase3(phase3)
    
    // 2. 注入知识同步回调 → 推送到 Gateway
    agent.SetKnowledgeSyncFn(func(topic, content string) {
        go syncKnowledgeToGateway(topic, content)
    })
    
    // 3. 注入记忆同步回调
    agent.SetMemorySyncFn(func(task, result string, success bool, learned string) {
        go syncMemoryToGateway(task, result, success, learned)
    })
}
```

#### syncKnowledgeToGateway 函数

```go
func syncKnowledgeToGateway(topic, content string) {
    gwURL := workerConfig.GatewayURL // http://127.0.0.1:8282
    entry := map[string]interface{}{
        "source": "ecs-p2ph",
        "type":   "lesson",
        "title":  topic,
        "content": content,
        "tags":   []string{"auto-generated", "after-action-review"},
        "confidence": 0.7,
        "ttl_days": 30,
    }
    body, _ := json.Marshal(entry)
    http.Post(gwURL+"/api/v1/knowledge/put", "application/json", bytes.NewReader(body))
}
```

### 3.2 方案 B — TriggerEngine 驱动复盘（推荐度中）

**思路**: 新增一个规则 action 类型 `trigger_agent_review`，在任务完成后由 TriggerEngine 触发 Agent 做一次针对性复盘。

**优点**: 更灵活，可以按规则精细化控制什么任务需要复盘  
**缺点**: 需要 TriggerEngine 和 Agent 之间有新的通信通道，改动较大

### 3.3 方案 C — 知识同步桥接（推荐度低）

**思路**: 单独开一个 goroutine 定期将 GitMemory 的新知识同步到 Gateway  
**优点**: 无侵入  
**缺点**: 有延迟，无法实时

### 3.4 方案对比

| 维度 | 方案 A (激活 Phase3) | 方案 B (Trigger 驱动) | 方案 C (桥接) |
|------|-------------------|--------------------|-------------|
| 改动量 | 40 行 | ~200 行 | ~100 行 |
| 是否利用现有代码 | ✅ 1.1K 行已写 | ⚠️ 部分 | ⚠️ 部分 |
| 实时性 | ✅ 同步 | ✅ 规则驱动 | ⚠️ 定时同步 |
| 灵活性 | ⚠️ 固定每5次 | ✅ 规则可控 | ⚠️ 全量同步 |
| 推荐 | **🏆 首选** | 远期优化 | 备选 |

---

## 📦 4. 数据结构

### 4.1 复盘条目 (存入 KnowledgeBase)

```json
{
  "source": "ecs-p2ph-agent",
  "type": "review",
  "title": "复盘: 远程执行Python脚本",
  "content": "## 成功经验\n- 使用Base64编码脚本传输可以避免引号嵌套问题\n- Gallery下载比curl更可靠\n\n## 失败原因\n- 未先检查Python3路径导致命令失败\n\n## 改进建议\n- 执行前先用 `which python3` 确认路径",
  "tags": ["python", "remote-exec", "review"],
  "confidence": 0.85,
  "ttl_days": 90
}
```

### 4.2 知识条目 (已有KnowledgeEntry格式)

```go
type KnowledgeEntry struct {
    ID         string   `json:"id"`
    Source     string   `json:"source"`
    Type       string   `json:"type"`       // skill / pattern / lesson / insight
    Title      string   `json:"title"`
    Content    string   `json:"content"`
    Tags       []string `json:"tags"`
    Confidence float64  `json:"confidence"`
    TTLDays    int      `json:"ttl_days"`
    Timestamp  string   `json:"timestamp"`
    TraceID    string   `json:"trace_id,omitempty"`
}
```

---

## 🛤️ 5. 实施计划

### Phase 3b.1 — 激活 Phase3（4小时）

- [ ] `worker_main.go`: 初始化时创建 `GalaxyPhase3Manager` 并调用 `agent.SetPhase3()`
- [ ] `worker_agent.go`: 注入 `knowledgeSyncFn` 和 `memorySyncFn`
- [ ] 编译测试：确认 Phase3 代码不再 dead code
- [ ] 验证：执行一个任务 → GitMemory 自动写入复盘

### Phase 3b.2 — 知识同步到 Gateway（4小时）

- [ ] 实现 `syncKnowledgeToGateway()` HTTP 调用
- [ ] Gateway 端确认 `POST /api/v1/knowledge/put` 正常工作
- [ ] 验证：Worker 写知识 → Gateway 知识库可查询到

### Phase 3b.3 — TriggerEngine 监工（可选，4小时）

- [ ] 新增 action type `learn` — 触发 Agent 做一次深度复盘
- [ ] 新增事件类型 `task_completed` — 任务完成时产生事件
- [ ] 配置 rules.yaml: `task_completed → learn` 规则

### Phase 3b.4 — Web 看板（可选，4小时）

- [ ] 在 `ai.html` 或 `memory.html` 上展示最近复盘
- [ ] Gateway 新增 `GET /api/v1/knowledge/reviews` 端点
- [ ] 展示：任务名称 / 经验摘要 / 置信度 / 来源节点

### 甘特图

```
任务                     | H1 | H2 | H3 | H4 | H5 | H6 | H7 | H8
Phase 3b.1 激活 Phase3   | ██ | ██ |    |    |    |    |    |
Phase 3b.2 知识同步      |    |    | ██ | ██ |    |    |    |
Phase 3b.3 Trigger监工   |    |    |    |    | ██ | ██ |    |
Phase 3b.4 Web看板       |    |    |    |    |    |    | ██ | ██
                         | 一天内可完成全部4步                          |
```

---

## ✅ 6. 验收标准

### 6.1 功能验收

| # | 验收项 | 方法 |
|---|--------|------|
| 1 | Agent 完成任务后自动调用 extractLesson | log 中出现 "📝 提取经验: ..." |
| 2 | GitMemory 自动保存复盘记录 | `git log --oneline` 看到复盘 commit |
| 3 | 复盘知识同步到 Gateway | `curl /api/v1/knowledge/query?q=review` 查到记录 |
| 4 | 其他Worker可查询共享知识 | 在节点B查询 `/api/v1/knowledge/query` |
| 5 | 知识持久化到 `data/knowledge/lesson/` | 目录下有 .md 文件 |

### 6.2 性能验收

| # | 指标 | 目标 |
|---|------|------|
| 1 | 复盘延迟 | ≤ 2 秒（LLM调用最慢） |
| 2 | 知识同步延迟 | ≤ 500 ms |
| 3 | 复盘对用户响应影响 | 0（goroutine异步） |

### 6.3 回归验收

```
# 现有测试全部通过
go test ./src/agent/...
go test ./src/gateway/...
go test ./src/kernel/...
go test ./src/composer/...

# 新增测试
go test -run TestPhase3 ./src/agent/...
go test -run TestKnowledgeSync ./src/gateway/...
```

---

## 📊 7. 后续演进

### Phase 3c — 探索沙盒

```
复盘数据积累了足够多经验后：
  → Agent 识别"还没有人试过的方法"
  → 在低负载时段自动设计A/B实验
  → 执行 → 记录 → 汇报
```

### Phase 3d — 自组织反馈

```
复盘经验 → 自动评估Agent能力变化
  → 发现某个Agent擅长某类任务
  → 自动调整任务分配策略（Scheduler集成）
  → 五智分工动态优化
```

---

## 🏗️ 8. 现有代码复用情况

| 现有代码 | 行数 | 状态 | 本设计如何利用 |
|---------|------|------|-------------|
| `galaxy_phase3.go` SelfLearningEngine | ~240行 | **🟡 已写但未激活** | 在 worker_main 中 SetPhase3 激活 |
| `galaxy_phase3.go` InnovationEngine | ~200行 | 🔴 未激活 | 后续 Phase 3c |
| `galaxy_phase3.go` CrossDomainEngine | ~300行 | 🔴 未激活 | 后续 Phase 3d |
| `galaxy_phase3.go` SelfOrgEngine | ~300行 | 🔴 未激活 | 后续 Phase 3d |
| `agent.go` SetKnowledgeSyncFn | 5行 | **🟡 已写但未调用** | worker_main 注入回调 |
| `agent.go` SetMemorySyncFn | 5行 | **🟡 已写但未调用** | worker_main 注入回调 |
| `gateway_knowledge.go` PUT/QUERY | 436行 | ✅ 生产就绪 | 直接调用 |
| `gateway_trigger.go` TriggerEngine | 1288行 | ✅ 生产就绪 | 同步到Gateway后用Trigger监控 |

**合计复用**: ~1,700 行已写代码将被激活，实际新增 ≤150 行。

---

## ⚠️ 9. 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| LLM 复盘结果噪音大 | 中 | confidence 阈值过滤，≤0.6 的知识不写入共享层 |
| 复盘阻塞任务完成 | 低 | goroutine 异步，不阻塞主流程 |
| 知识库膨胀 | 低 | TTL过期自动清理，每1000条触发压缩 |
| Worker 重启丢失未同步知识 | 低 | knowledgeSyncFn 同步失败时写本地队列重试 |

---

## 📝 10. 附录

### A. SelfLearningEngine 当前代码状态

```go
// agent.go:494-495  — 已接入但 Phase3 为 nil
if a.Phase3 != nil {
    a.Phase3.OnTaskCompleted(task, plan, resultStr, success)
}

// galaxy_phase3.go:48  — 构造函数就绪
func NewSelfLearningEngine(agent, memory, llm) → *SelfLearningEngine

// galaxy_phase3.go:66  — 核心逻辑
func (sle) OnTaskCompleted(task, plan, result, success) {
    sle.extractLesson(...)      // 提取经验
    sle.distillKnowledge(...)   // 知识蒸馏
    sle.reflect()               // 定期反思
}
```

### B. 相关文档索引

| 文档 | 说明 |
|------|------|
| `GALAXY-PLAN.md` | 银河计划 v2.0 — 总体规划 |
| `SPEC-TRIGGER-001` | TriggerEngine 设计规范 |
| `SPEC-MEMORY-001` | Git记忆系统设计规范 |
| `SPEC-DMEM-001` | 集群共享记忆层设计规范 |
| `SPEC-GALAXY-003` | 银河计划 Phase 3 设计规范 |
| `knowledge-sharing-protocol.md` | KSP-001 知识共享协议 |

---

*设计文档到此结束。下一步：老大评审 → 确认方案 → 我开干 Phase 3b.1。*