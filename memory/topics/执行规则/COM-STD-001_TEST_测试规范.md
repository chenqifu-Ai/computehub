# 🧪 COM-STD-001-TEST 集群跨节点通信测试规范（v1.0）

> 制定时间：2026-06-10
> 制定人：端智 💻
> 适用：COM-STD-001 v1.0 标准所有通信通道的测试

---

## 📋 测试总纲

### 测试分层

```
L1 ── 单元测试 ── 单模块功能验证（Go test）
  │
L2 ── 集成测试 ── 通道级端到端验证（Python 脚本）
  │
L3 ── E2E 测试 ── 多通道联合场景（全链路）
  │
L4 ── 混沌测试 ── 故障注入 + 恢复验证
```

### 测试覆盖矩阵

| 通道 | L1 | L2 | L3 | L4 | 优先级 |
|------|:--:|:--:|:--:|:--:|:------:|
| ① SSH | ✅ | ✅ | ✅ | ✅ | P0 |
| ② Task API | ✅ 已有 | ✅ 新增 | ✅ | ⬜ | P0 |
| ③ Gateway HTTP | ✅ 已有 | ✅ 新增 | ✅ | ⬜ | P0 |
| ④ WebSocket | ⬜ | ✅ 新增 | ✅ | ⬜ | P1 |
| ⑤ proot→agent AI对话 | ⬜ | ✅ 新增 | ✅ | ⬜ | P0 ⭐ |
| ⑥ 广播 | ⬜ | ✅ 新增 | ✅ | ⬜ | P1 |
| ⑦ WMI (Windows) | ⬜ | ✅ 新增 | ✅ | ⬜ | P1 |
| ⑧ gRPC (新建) | ⬜ | ✅ 新建方案 | ⬜ | ⬜ | P2 |
| ⑨ 文件传输 (新建) | ⬜ | ✅ 新建方案 | ⬜ | ⬜ | P2 |

**P0**: 必须通过才能发布 → P1: 每次发布前验证 → P2: 下个迭代

### 节点测试矩阵（实机）

| 节点 | 平台 | 状态 | 测试角色 |
|------|------|:----:|---------|
| ecs-p2ph | linux/amd64 | ✅ | 网关端、SSH目标、AI目标 |
| worker-arm | android/arm64 | ✅ | Worker客户端、AI对话源 |
| windows-mobile | windows/amd64 | ✅ | WMI目标、跨平台兼容 |
| xiaomi-table | linux/arm64 | ❌ 离线 | proot→agent 完整链路（待恢复） |
| wanlida-opc01 | ? | ❌ 离线 | 扩展验证（待恢复） |

---

## 🔬 L1 单元测试

### 现有测试清单（已验证通过）

```
src/gateway/gateway_test.go          — health/status/register/list/task/heartbeat/dispatch/metrics
src/gateway/auth_test.go             — 鉴权
src/agent/agent_integration_test.go  — Agent + Memory 全链路
src/agent/memory_test.go             — 记忆仓库
src/agent/deep_integration_test.go   — 深度集成
src/composer/client_test.go          — LLM 客户端
src/composer/composer_test.go        — 编排器
src/discover/discover_test.go        — 发现服务
src/executor/executor_test.go        — 执行器
src/scheduler/..._test.go            — 调度器/队列/熔断
src/gateway/gallery_test.go          — Gallery
src/gateway/gateway_core_test.go     — 核心逻辑
src/health/health_test.go            — 健康检查
src/kernel/..._test.go               — 内核
src/monitor/monitor_test.go          — 监控
src/tuicmd/tui_main_test.go          — TUI
src/visualizer/aggregator_test.go    — 聚合器
src/workercmd/upgrade_engine_test.go — 升级引擎
src/workercmd/upgrade_manager_test.go — 升级管理器
```

### 新增单元测试（L1 补充）

需新增的 Go test 文件：

| 文件 | 测试内容 | 优先级 |
|------|---------|:------:|
| `src/gateway/broadcast_test.go` | 广播消息的路由与分发 | P1 |
| `src/gateway/ws_test.go` | WebSocket 消息处理 | P2（需 WS 实现就绪） |
| `src/workercmd/grpc_test.go` | gRPC 通道（新建后） | P2 |
| `src/agent/cross_node_test.go` | 跨节点请求构造与解析 | P1 |

---

## 🧩 L2 集成测试

### 测试脚本架构

```bash
scripts/
  test_com_std_001.sh        # 【入口】一键运行所有通信测试
  test_com_001_ssh.sh        # 测试 ① SSH
  test_com_002_task.sh       # 测试 ② Task API
  test_com_003_http.sh       # 测试 ③ Gateway HTTP
  test_com_004_ws.sh         # 测试 ④ WebSocket
  test_com_005_proot.sh      # 测试 ⑤ proot→agent AI 对话
  test_com_006_broadcast.sh  # 测试 ⑥ 广播
  test_com_007_wmi.sh        # 测试 ⑦ WMI (Windows)
  test_com_report.sh         # 生成测试报告
```

### ① SSH 连接测试

```yaml
测试用例: SSH-001
描述: SSH 密钥认证 + 命令执行
前置条件: 
  - id_ed25519_computehub 密钥存在
  - ECS 8022 端口可达
步骤:
  1. ssh -o ConnectTimeout=5 -i <key> -p 8022 computehub@36.250.122.43 "hostname"
  2. ssh -o ConnectTimeout=5 -i <key> -p 8022 computehub@36.250.122.43 "uptime"
预期结果:
  - 返回 hostname: 匹配 ecs-xxx
  - 返回 uptime: 格式正确
  - exit_code = 0
通过标准: 3/3 次连接成功，平均延迟 < 100ms
```

```yaml
测试用例: SSH-002
描述: SSH 无密码连接（密钥仅此一把）
步骤:
  1. 不加 -i 参数尝试 ssh -p 8022 computehub@36.250.122.43 "hostname"
预期结果:
  - 连接被拒 / Permission denied
通过标准: 密钥之外的认证方式不可用
```

### ② Task API 测试

```yaml
测试用例: TASK-001
描述: 提交简单命令到各节点
节点: ecs-p2ph / worker-arm / windows-mobile
步骤:
  1. POST /api/v1/tasks/submit → {node_id, command: "echo HELLO_COM_STD"}
  2. 等待 5s
  3. GET /api/v1/tasks/detail?task_id=xxx → 检查 status=completed, stdout
预期结果:
  - 各节点均返回 "HELLO_COM_STD"
  - exit_code = 0
  - 耗时: ecs-p2ph < 5s, worker-arm < 10s, windows-mobile < 15s
通过标准: 全节点回显一致
```

```yaml
测试用例: TASK-002
描述: 命令超时处理
步骤:
  1. POST /api/v1/tasks/submit → {command: "sleep 60", timeout: 5}
  2. 等待 10s
  3. GET /api/v1/tasks/detail → 检查 status
预期结果:
  - status = "timed_out" 或 "failed"
  - 命令在 5s 后被 kill
通过标准: 超时机制正确触发
```

```yaml
测试用例: TASK-003
描述: 高优先级抢占队列
步骤:
  1. 提交 3 个 priority=1 的命令到同一节点
  2. 再提交 1 个 priority=10 的命令
  3. 观察执行顺序
预期结果:
  - priority=10 首先被执行
通过标准: 优先级排序正确
```

### ③ Gateway HTTP API 测试

```yaml
测试用例: HTTP-001
描述: 全部管理端点可达
步骤:
  1. GET  /api/health → 200
  2. GET  /api/status → 200, kernel=RUNNING
  3. GET  /api/v1/nodes/list → 200, data 包含所有注册节点
  4. GET  /api/v1/tasks/list → 200
  5. GET  /api/v1/agents/list → 200
  6. GET  /api/v1/hall/topics → 200
预期结果: 所有端点返回 200
通过标准: 100% 端点可达
```

```yaml
测试用例: HTTP-002
描述: 错误路径返回 404
步骤:
  1. GET /api/non-existent-path
  2. POST /api/v1/tasks/submit (空 body)
预期结果: 返回 404 / 400
通过标准: 正确返回 HTTP 错误码
```

### ④ WebSocket 测试

```yaml
测试用例: WS-001
描述: 本机 WebSocket 连通性
节点: worker-arm (8383 有 Agent UI 和 WS)
步骤:
  1. 从 worker-arm 本机连接 ws://localhost:8383
  2. 发送测试消息
  3. 接收回复
预期结果: WebSocket 握手成功，消息可达
通过标准: 成功建立连接并双向通信
```

```yaml
测试用例: WS-002
描述: 跨节点 WebSocket 不可达
步骤:
  1. 从端智尝试连接 ws://worker-arm:8383
预期结果: 连接失败或被防火墙拦截
通过标准: WS 端口未暴露到公网
```

### ⑤ proot→agent AI 对话测试 ⭐

```yaml
测试用例: AI-001
描述: 跨节点 AI 基础对话可用
节点: 端智 → ecs-p2ph
步骤:
  1. 端智提交 Task → ecs-p2ph → openclaw agent --message "你好，请回复 OK"
  2. 等待回复
预期结果:
  - 响应中包含 "OK"
  - 总耗时 < 60s
通过标准: AI 回复非空且相关
```

```yaml
测试用例: AI-002
描述: AI 对话超时处理
步骤:
  1. 提交 Task → timeout=5, command="proot-distro login ubuntu ... openclaw agent ..."
预期结果:
  - Task 超时，返回 status=timed_out
通过标准: 超时机制不阻塞队列
```

```yaml
测试用例: AI-003
描述: 复杂指令（含中文、特殊字符）
步骤:
  1. 用 base64 编码消息："查询系统状态并分析内存使用情况"
  2. 提交 Task → 节点通过 base64 -d 解码后传给 openclaw agent
预期结果:
  - 中文指令被正确理解并回复
通过标准: 中文字符不丢失、不乱码
```

### ⑥ 广播测试

```yaml
测试用例: BC-001
描述: 向所有节点发送广播消息
步骤:
  1. POST /api/v1/cluster/broadcast → {message: "COM-STD-001 broadcast test"}
预期结果: 所有在线节点收到广播
通过标准: 至少 1 个节点响应（没有注册回调则不要求特定响应）
```

```yaml
测试用例: BC-002
描述: 广播 Payload 边界测试
步骤:
  1. POST 广播 payload=1KB
  2. POST 广播 payload=100KB
  3. POST 广播 payload=1MB
预期结果: 1KB 和 100KB 成功，1MB 可能被限
通过标准: 不崩溃，大小限制明确
```

### ⑦ WMI 测试（Windows）

```yaml
测试用例: WMI-001
描述: Windows 节点可通过 Task API 执行 WMI 查询
节点: windows-mobile
步骤:
  1. POST /api/v1/tasks/submit → {node_id:"windows-mobile", command:"wmic os get caption"}
  2. 等待返回
预期结果:
  - 返回 Windows OS 版本信息
  - exit_code = 0
通过标准: WMI 命令正确执行
```

```yaml
测试用例: WMI-002
描述: WMI 在非 Windows 节点不可用
节点: ecs-p2ph / worker-arm
步骤:
  1. 向 Linux 节点提交 wmic 命令
预期结果:
  - "command not found" 或 exit_code != 0
通过标准: Linux 节点不执行 WMI
```

---

## 🔗 L3 E2E 全链路测试

### 场景一：跨节点 AI 对话链路

```
端智 (Termux) → Gateway (8282) → ecs-p2ph → openclaw agent → LLM → 回复 → 原路返回
```

```yaml
用例: E2E-001 - 跨节点 AI 对话全链路
步骤:
  1. 端智 → Gateway: submit task to ecs-p2ph
  2. ecs-p2ph: 执行 openclaw agent --message "请用中文介绍你自己"
  3. 轮询 Task 结果
  4. 验证回复是中文且合理
通过标准: 完整链路 100% 通过，含 LLM 推理总耗时 < 120s
```

### 场景二：三节点协同运维

```
端智 → Gateway → ecs-p2ph (查CPU) + worker-arm (查内存) + windows-mobile (查磁盘)
                → 汇总结果 → 发送邮件报告
```

```yaml
用例: E2E-002 - 三节点同时查询
步骤:
  1. 同时提交 3 个 Task（不同节点）
  2. 收集所有返回结果
  3. 汇总为 JSON 报告
通过标准: 三节点全部响应，无超时
```

### 场景三：广播 + 确认

```
端智 → Gateway: broadcast "5分钟后维护"
      ecs-p2ph: 收到 → 回确认
      worker-arm: 收到 → 回确认
      windows-mobile: 收到 → 回确认
```

```yaml
用例: E2E-003 - 广播确认机制
步骤:
  1. POST broadcast + callback 机制
  2. 轮询确认每个节点已收到
通过标准: 在线节点确认率 100%
```

### 场景四：自动升级通道

```yaml
用例: E2E-004 - 跨节点升级流程
步骤:
  1. 部署新 binary 到 deploy/
  2. 等待 Worker 自动检查升级
  3. 验证版本号更新
通过标准: Worker 在 30 分钟内完成升级
```

---

## 💥 L4 混沌测试

### 故障注入

```yaml
用例: CHAOS-001 - 节点离线恢复
步骤:
  1. stop ecs-p2ph Worker 进程
  2. 观察 Gateway 节点状态变为 offline
  3. restart Worker
  4. 观察节点自动重新注册
通过标准: 自动恢复时间 < 60s
```

```yaml
用例: CHAOS-002 - 网络分区
步骤:
  1. iptables drop 目标节点 8282 端口
  2. 观察 Task 超时处理
  3. iptables restore
  4. 观察恢复
通过标准: Task 不卡死，恢复后处理正确
```

```yaml
用例: CHAOS-003 - 并发压力
步骤:
  1. 同时提交 50 个 Task 到同一个节点
  2. 观察队列管理
  3. 验证无 Task 丢失
通过标准: 50/50 Task 全部完成，无丢失
```

```yaml
用例: CHAOS-004 - 消息损坏
步骤:
  1. 提交 payload 含非法字符 / 二进制数据
  2. 验证 JSON 解析失败被正确处理
通过标准: 返回 400 错误，不崩溃
```

---

## 📊 测试报告模板

### 单次测试报告

```markdown
# COM-STD-001 通信标准测试报告

时间: 2026-06-10 14:30
执行人: 端智

## 执行摘要
- 总用例: 20
- 通过: 18 (90%)
- 失败: 2
- 阻塞: 0

## 失败详情
| 用例ID | 通道 | 失败原因 | 严重程度 |
|--------|------|---------|:--------:|
| AI-001 | ⑤ proot | xiaomi-table 离线 | ⚠️ 中 |

## 性能数据
| 通道 | P50 | P95 | P99 |
|------|:---:|:---:|:---:|
| ① SSH | 45ms | 82ms | 120ms |
| ② Task | 210ms | 1.2s | 3.5s |
| ③ HTTP | 5ms | 12ms | 28ms |
| ⑤ AI | 18s | 45s | 78s |

## 结论
[通过/不通过/有条件通过]
```

### 自动化报告

测试脚本运行后自动生成 JSON + Markdown 报告：
```
reports/
  com-std-001-test-2026-06-10.json
  com-std-001-test-2026-06-10.md
```

---

## ⚡ 执行流程

### 每日检查（轻量）

```bash
# 仅检查 ②③⑥ — 快速验证通道可用
./scripts/test_com_002_task.sh --quick
./scripts/test_com_003_http.sh --quick
./scripts/test_com_006_broadcast.sh --quick
```

### 提交前检查（中量）

```bash
# 跑 L2 全部 P0 用例，约 5 分钟
./scripts/test_com_std_001.sh --level L2 --priority P0
```

### 发布前检查（全量）

```bash
# 跑 L2+L3 全部用例，约 30 分钟
./scripts/test_com_std_001.sh --level L2,L3
```

### 混沌测试（周期性）

```bash
# 跑 L4 混沌测试，需手动恢复，约 10 分钟
./scripts/test_com_std_001.sh --level L4
```

---

## 🔧 测试结果判定标准

| 等级 | 判定 | 条件 |
|:----:|------|------|
| ✅ 通过 | 无失败用例 | 100% 通过 |
| ⚠️ 有条件通过 | 失败 ≤ 2 且非 P0 | 可以上线但需修复 |
| ❌ 不通过 | 失败 ≥ 3 或 P0 失败 | 不允许上线 |
| 🚫 阻塞 | 节点离线导致无法测试 | 等待恢复 |

---

## 📁 测试脚本规范

### 命名规则

```
test_com_<编号>_<通道名>.sh
```

### 脚本结构模板

```bash
#!/bin/bash
# COM-STD-001-TEST：<通道名> 集成测试
# 用例: <用例ID> <用例ID> ...
set -e

GATEWAY="http://36.250.122.43:8282"
PASS=0
FAIL=0

test_case() {
    local name="$1"
    echo "  [TEST] $name..."
    if eval "$2"; then
        echo "    ✅ PASS"
        ((PASS++))
    else
        echo "    ❌ FAIL"
        ((FAIL++))
    fi
}

echo "=== 🧪 <通道名> 测试 ==="

test_case "TASK-001" '
    result=$(curl -sf -X POST "$GATEWAY/api/v1/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{\"node_id\":\"ecs-p2ph\",\"command\":\"echo OK\",\"timeout\":10}")
    echo "$result" | grep -q "success.*true"
'

echo ""
echo "结果: $PASS 通过 / $FAIL 失败"
exit $FAIL
```

---

## 🚀 执行计划

| 阶段 | 内容 | 时间 | 负责人 |
|:----:|------|:----:|:------:|
| 1️⃣ | 编写全部 L2 测试脚本（P0） | 立即 | 端智 |
| 2️⃣ | 在线节点跑通 P0 用例 | 紧随 1️⃣ | 端智 |
| 3️⃣ | 编写 L3 E2E 场景脚本 | 1️⃣ 完成后 | 端智 |
| 4️⃣ | 混沌测试 L4 手动验证 | 3️⃣ 完成后 | 端智 |
| 5️⃣ | 自动化报告集成 | 4️⃣ 完成后 | 端智 |
| 6️⃣ | 完善 v1.1 标准（gRPC + 文件传输 + mTLS） | 5️⃣ 完成后 | 四智协商 |

---

*测试规范版本 v1.0 — 2026-06-10 端智制定*