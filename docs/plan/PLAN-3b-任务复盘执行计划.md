# 🎯 Phase 3b 执行计划（细化版）

**总工期**: 4 小时 | **新增代码**: ≤ 50 行 | **激活代码**: ~600 行  
**依赖**: 无（全部依赖已就绪）

---

## 1️⃣ 精确现状（已经确认的代码）

### 已经连好的（不需要改）

```
agent.go:494     → if a.Phase3 != nil { a.Phase3.OnTaskCompleted(...) }    ✅
agent.go:497-499 → if a.memorySyncFn != nil { a.memorySyncFn(...) }        ✅
agent.go:501-503 → if a.knowledgeSyncFn != nil { ... }                      ✅
worker_agent.go:601 → agt.SetMemorySyncFn(...)                              ✅
worker_agent.go:606 → agt.SetKnowledgeSyncFn(...)                           ✅
gateway.go:746-768  → /api/v1/knowledge/* 路由注册                          ✅
gateway_knowledge.go → KnowledgeStore CRUD 完整                             ✅
```

### 唯一断开的链路

```
worker_agent.go:557 → agent.NewAgent(llm, tools, "")     # Agent 已创建
worker_agent.go:601 → SetMemorySyncFn(...)               # 记忆同步已注入
worker_agent.go:606 → SetKnowledgeSyncFn(...)            # 知识同步已注入
                     ❌ 缺少 agent.SetPhase3(...)         # 这是唯一缺失的一行
```

**Phase3 创建需要**: `NewGalaxyPhase3Manager(agent, expertRegistry, memory, llm)`

| 参数 | 来源 | 状态 |
|------|------|------|
| `agent` | `startWorkerAgent` 中的 `agt` | ✅ 已有 |
| `expertRegistry` | `agent.NewExpertRegistry(llm)` | 🔴 需创建 |
| `memory` | `agt.GetMemory()` | ✅ Agent.SetMemory 已实现 |
| `llm` | `startWorkerAgent` 中的 `llm` | ✅ 已有 |

---

## 2️⃣ 分步骤执行

### Step 1: 激活 Phase3（15 分钟）

**改 1 个文件**: `src/workercmd/worker_agent.go`

**改动位置**: 在 `startWorkerAgent()` 中，`SetKnowledgeSyncFn` 之后、HTTP 服务器创建之前插入。

```go
// 在 worker_agent.go 的 startWorkerAgent() 中，约 line 610 附近插入：

	// 🌌 银河计划 Phase 3b: 自主进化引擎
	// 任务完成后自动提取经验 + 知识蒸馏 + 定期反思
	expertRegistry := agent.NewExpertRegistry(llm)
	expertRegistry.RegisterDefaults() // 注册默认专家
	phase3 := agent.NewGalaxyPhase3Manager(agt, expertRegistry, agt.GetMemory(), llm)
	agt.SetPhase3(phase3)
	fmt.Printf(" %s🌌 Phase 3b 自主进化引擎已激活 (agent=%s)%s\n", green(bold("")), state.nodeID, reset())
```

**依赖**: 确保 import 已有 `"github.com/computehub/opc/src/agent"`（已有，该文件已经 import agent 包）

**验证**:
```bash
cd /home/computehub/ComputeHub && go build ./src/workercmd/  # 编译通过
```

---

### Step 2: 验证链路（30 分钟）

**不上生产，本地测试**:

```bash
# 1. 构建带 Phase3 的 binary
go build -o /tmp/computehub-phase3 ./cmd/computehub/

# 2. 启动 Gateway（使用 test 端口，避免冲突）
/tmp/computehub-phase3 gateway --port 9292 &
GW_PID=$!
sleep 2

# 3. 启动 Worker（必需 --agent 才能激活 Phase3）
/tmp/computehub-phase3 worker --agent --gw http://127.0.0.1:9292 --node-id test-phase3 --interval 3 --concurrent 2 &
WK_PID=$!
sleep 3

# 4. 提交一个测试任务
curl -s -X POST http://127.0.0.1:9292/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"node_id":"test-phase3","command":"echo hello phase3","timeout":10}'

# 5. 等待几秒，看 Phase3 是否触发
sleep 8

# 6. 验证知识库有数据
curl -s http://127.0.0.1:9292/api/v1/knowledge/query?q=phase3 | python3 -m json.tool

# 7. 验证本地 GitMemory 有复盘 commit
cd /tmp/test-memory && git log --oneline -5

# 8. 验证 agent API
curl -s http://127.0.0.1:9292/api/v1/trigger/stats | python3 -m json.tool

# 9. 清理
kill $WK_PID $GW_PID 2>/dev/null
```

**验收**:
- ✅ `go build` 编译通过
- ✅ Worker Agent 日志输出 `🌌 Phase 3b 自主进化引擎已激活`
- ✅ 任务执行后，自动生成复盘（GitMemory 能看到 commit）
- ✅ 复盘知识同步到 Gateway（`/api/v1/knowledge/query` 能查到）

---

### Step 3: 生产部署（30 分钟）

```bash
# 1. 全量编译
cd /home/computehub/ComputeHub
./scripts/build_all.sh

# 2. 上传到 Gallery
./scripts/gallery-upload.sh deploy/linux-amd64/computehub

# 3. 升级 Gateway
systemctl restart computehub-gateway

# 4. 升级 Worker（自动升级循环会处理，或手动触发）
systemctl restart computehub-worker

# 5. 验证生产日志
journalctl -u computehub-worker --since "5 min ago" | grep "Phase 3b"
journalctl -u computehub-gateway --since "5 min ago" | grep "knowledge/put"
```

---

### Step 4: 验证生产（15 分钟）

```bash
# 1. 节点都上线
curl -s http://localhost:8282/api/v1/nodes | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} nodes online')"

# 2. 提交生产任务
curl -s -X POST http://localhost:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"node_id":"ecs-p2ph","command":"echo test-phase3-production","timeout":10}'

# 3. 等 10 秒，查知识库
curl -s http://localhost:8282/api/v1/knowledge/query?q=test | python3 -m json.tool

# 4. 检查 TriggerEngine 统计
curl -s http://localhost:8282/api/v1/trigger/stats | python3 -m json.tool
```

---

## 3️⃣ 文件改动清单

| 文件 | 改动类型 | 新增行数 | 风险 |
|------|---------|---------|------|
| `src/workercmd/worker_agent.go` | 新增调用来激活 Phase3 | **5 行** | 极低 |
| `src/agent/galaxy_phase3.go` | 无改动（代码已写） | 0 行 | ✅ |
| `src/agent/agent.go` | 无改动（回调已接入） | 0 行 | ✅ |
| `src/gateway/gateway_knowledge.go` | 无改动（API 已注册） | 0 行 | ✅ |

**总计新增: 5 行代码，激活 ~600 行现有代码。**

---

## 4️⃣ 验证矩阵

| # | 验收项 | 预期 | 验证方法 |
|---|--------|------|---------|
| 1 | 编译通过 | `go build ./...` 返回 0 | `go build ./cmd/computehub/` |
| 2 | Worker 启动日志 | 打印 `🌌 Phase 3b 自主进化引擎已激活` | 查看日志 |
| 3 | 任务完成后自动提取经验 | GitMemory 出现复盘 commit | `git log --oneline` |
| 4 | 知识同步到 Gateway | `/api/v1/knowledge/query` 返回有数据 | curl 查询 |
| 5 | 知识持久化 | `data/knowledge/lesson/` 下有 .md 文件 | `ls data/knowledge/lesson/` |
| 6 | 现有测试不坏 | `go test ./src/agent/... && go test ./src/gateway/...` 全绿 | 跑测试 |
| 7 | 生产节点存活 | Gateway + Worker 正常提供服务 | `curl /api/v1/nodes` |

---

## 5️⃣ 风险与回滚

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Phase3 内部 LLM 调用 timeout | 中 | 复盘失败，不影响主流程 | goroutine 异步，默认 30s timeout |
| 知识同步 HTTP 调用失败 | 中 | 知识存本地但不回传 Gateway | KnowledgeSyncFn 内部有 fallback（先存本地） |
| ExpertRegistry 注册了不存在 | 低 | CrossDomain/SelfOrg 部分失效 | 先只激活 SelfLearning 部分 |
| 磁盘写满 | 极低 | GitMemory commit 失败 | 有 error log 但任务不受影响 |

**回滚方案**:
```bash
# 方法 1: 删除 SetPhase3 行，重编译重部署
# 方法 2: deploy/ 有 bak，systemctl restart 回旧版
cp deploy/linux-amd64/computehub.bak deploy/linux-amd64/computehub
systemctl restart computehub-gateway
systemctl restart computehub-worker
```

---

## 6️⃣ 时间线

```
T+0m   读取现有代码确认状态（已完成）
T+10m  编写 Step 1 代码（5 lines in worker_agent.go）
T+15m  编译验证
T+20m  go build ./... 全量编译，确认不破坏现有测试
T+30m  启动本地测试 Gateway + Worker
T+45m  提交测试任务，验证链路
T+60m  全量编译 5 平台 + Gallery 上传
T+70m  生产部署 Gateway + Worker 升级
T+80m  生产验证
T+90m  全部完成 ✅
```

---

## 7️⃣ 如果需要进一步调整

如果老大确认方案后还想加东西，可以额外做：

- **配置开关**: 加环境变量 `PHASE3_ENABLED=true/false` 控制是否激活（防止未来需要禁用）
- **调试日志**: Phase3 每一步加结构化日志，跟踪复盘过程
- **阈值可配**: reflectInterval（默认5次）、confidence 阈值等

但上述都是锦上添花，**核心 5 行代码就能跑通全链路**。要现在开干吗？