# ComputeHub 测试流程规范 (STD-TEST-001)

**生效**: 2026-05-09
**版本**: v2.0
**测试脚本**: `projects/computehub/tests/test_computehub.py`
**最新测试结果**: 21/21 全通过 (2026-05-09 07:17)

---

## 📋 规范地图

```
接手（5秒）
  ├─ 前置条件检查（3项）
  ├─ 环境快照（不用探测）
  ├─ 运行测试
  ├─ 解读结果
  │    ├─ 通过 → 汇报
  │    └─ 失败 → 故障排查（6种模式）
  │               ├─ 网关不通
  │               ├─ Worker不在线
  │               ├─ 任务提交失败
  │               ├─ 任务执行错误
  │               ├─ 测试脚本报错
  │               └─ 代码编译失败
  └─ 修改验证流程
```

---

## 1. 前置条件（接手后5秒检查）

```
🚨 铁律：不要重新配环境，不要重复探测
🚨 铁律：先查 git 再查文件系统（git ls-files | grep）
✅ 直接验证以下3项，都通过就测
```

### 1.1 网关存活
```bash
curl -s http://192.168.1.7:8282/api/health
# 预期: {"success":true,"data":"ComputeHub System Healthy"}
```

### 1.2 至少一个 Worker 在线
```bash
curl -s http://192.168.1.7:8282/api/v1/nodes/list
# 预期: data[] 不为空，所有节点的 status 都是 online
```

### 1.3 测试脚本存在
```bash
cd /root/.openclaw/workspace
git ls-files | grep test_computehub
# 或用绝对路径检查
ls -la projects/computehub/tests/test_computehub.py
```

**如果 1.1 不通 → 看 5.1「网关起不来」**
**如果 1.2 无 Worker → 看 5.2「Worker不在线」**
**如果 1.3 不存在 → 从 git 恢复：`git checkout -- projects/computehub/tests/test_computehub.py`**

---

## 2. 运行测试

### 2.1 标准流程

```bash
cd /root/.openclaw/workspace/projects/computehub

# 如果还没装 requests
pip install requests 2>/dev/null

# 跑全部
python3 tests/test_computehub.py
```

**预期结果**: ✅ 21 项通过，❌ 0 项失败

### 2.2 单组调试

```bash
python3 tests/test_computehub.py health    # 只看网关
python3 tests/test_computehub.py nodes     # 只看节点管理
python3 tests/test_computehub.py tasks     # 只看任务生命周期
python3 tests/test_computehub.py stream    # 只看流式输出
python3 tests/test_computehub.py errors    # 只看错误处理
python3 tests/test_computehub.py metrics   # 只看指标
python3 tests/test_computehub.py priority  # 只看优先级
```

### 2.3 列出所有组

```bash
python3 tests/test_computehub.py --list
```

### 2.4 指定不同网关（如果改了地址）

```bash
python3 tests/test_computehub.py --gateway http://新IP:新端口
```

---

## 3. 测试覆盖说明

### 3.1 测试分组

| # | 组名 | 测试项数 | 测什么 | 失败时表示 |
|---|------|---------|-------|----------|
| 1 | health | 3 | 存活、状态、节点列表基础查询 | Gateway 挂了或路由配错 |
| 2 | nodes | 5 | 注册→列表验证→心跳→注销→确认移除 | NodeManager API 有问题 |
| 3 | tasks | 7 | 提交→poll认领→完成→detail→progress→错误命令exit_code | **核心流水线断裂** |
| 4 | list | 1 | 任务列表查询 + 统计汇总 | List 接口异常 |
| 5 | errors | 4 | 空参数、不存在ID的边界处理 | 边界防护缺失 |
| 6 | stream | 1 | 模拟Worker推送→累积验证 | Progress流式链路断 |
| 7 | priority | 1 | 多优先级任务提交 | 调度注册异常 |
| 8 | metrics | 1 | 节点性能指标 | Prometheus采集异常 |

### 3.2 测试路径图

```
提交任务 ──→ Worker poll认领 ──→ 执行命令 ──→ 写入结果
  │                                              │
  ├─ task_id 必须手动生成                          ├─ detail?task_id=xxx 查完整结果
  ├─ command 按 Worker 平台写                      ├─ progress?task_id=xxx 查流式输出
  │  (Windows: &, Linux: &&)                      └─ exit_code / stdout / stderr
  └─ node_id 必须指定                             均已验证
```

### 3.3 API 端点清单（已验证可用）

| 方法 | 路径 | 用途 | 必需参数 |
|------|------|------|---------|
| GET | `/api/health` | 存活检查 | 无 |
| GET | `/api/status` | 系统状态 | 无 |
| POST | `/api/v1/nodes/register` | 注册节点 | node_id |
| POST | `/api/v1/nodes/unregister` | 注销节点 | node_id |
| POST | `/api/v1/nodes/heartbeat` | 心跳 | node_id |
| GET | `/api/v1/nodes/list` | 节点列表 | 无 |
| GET | `/api/v1/nodes/metrics` | 节点指标 | node_id |
| POST | `/api/v1/tasks/submit` | 提交任务 | task_id, node_id, command |
| POST | `/api/v1/tasks/poll` | Worker认领 | node_id |
| GET | `/api/v1/tasks/detail` | 任务详情 | task_id, node_id |
| GET | `/api/v1/tasks/progress` | 流式输出 | task_id |
| POST | `/api/v1/tasks/progress` | 推送输出 | task_id, node_id, stdout |
| GET | `/api/v1/tasks/list` | 任务列表 | 无 |
| POST | `/api/v1/tasks/cancel` | 取消任务 | task_id |

---

## 4. 环境快照（接手即知，不需要重新探测）

```
🚨 以下信息是固化现状，不是"建议"，是"事实"
🚨 接手后不要重新 ping、不要重新扫端口、不要重新查架构
```

### 4.1 硬件拓扑

```
本机 (OpenClaw网关)
   ├─ IP: 192.168.1.7
   ├─ 系统: Linux aarch64 (ARM64)
   ├─ 角色: Gateway 主机
   └─ 内存: 紧张（Swap 重度使用 8GB/11GB）
   
cqf-worker-02 (Windows笔记本)
   ├─ IP: 动态 (通过 Gateway 自动注册)
   ├─ 机器: LAPTOP-QOVCUVAG
   ├─ 系统: Windows 10.0.26200
   ├─ CPU: 13th Gen i5-13500H (14核)
   ├─ 内存: 16GB (8×2GB DDR)
   ├─ 磁盘: C:195G + D:562G + E:195G
   ├─ GPU: 无 (CPU模式)
   └─ 状态: ✅ 在线，已执行19个任务全部成功

cqf-worker-01 (GPU服务器, ❌ 未接入)
   ├─ IP: 192.168.1.8
   ├─ 系统: Linux x86_64 (待确认)
   ├─ GPU: H100 (来自旧日志)
   ├─ 端口: 22(SSH), 11434(Ollama: glm-4.6:cloud)
   ├─ SSH: ❌ 没有配置免密 (密钥在 ~/.ssh/id_ed25519, 需要密码)
   ├─ Worker状态: 还在跑，但连的是旧地址 192.168.1.4:8282 (已不存在)
   └─ 接入前需要: 密码问老大 + x86_64 worker 二进制 (现有的是 ARM64)
```

### 4.2 运行中进程

```
computehub-gateway    PID 5218   新 Worker Gateway v0.7.0 ✅
openclaw-gateway      PID 11827  旧 OpenClaw Gateway        ⚠️ 不影响，可忽略
computehub-tui        PID 24952  终端 UI                     ⚠️ 不影响，可忽略
```

**两个 Gateway 共存没事，端口不同不影响测试。**

### 4.3 代码与二进制位置

```
/root/.openclaw/workspace/projects/computehub/
├── config.json                 ← Gateway 配置 (含 composer/ollama 设置)
├── genes.json                  ← Gene 存储
├── deploy/ubuntu/bin/
│   ├── computehub-gateway      ← ARM64 二进制 (8.7MB)
│   └── computehub-worker       ← ARM64 二进制 (8.4MB) ❌ 不能用于 x86_64 的 1.8
├── src/
│   ├── gateway/
│   │   ├── gateway.go          ← 主入口 + API路由
│   │   └── gateway_worker.go   ← Worker通信API实现
│   ├── kernel/
│   │   ├── actions.go          ← NodeManager + 任务调度核心
│   │   └── kernel.go           ← Kernel主逻辑
│   ├── executor/               ← 命令执行器
│   └── scheduler/              ← 优先级调度 + 抢占
└── tests/
    └── test_computehub.py      ← 测试脚本 (461行, 21项测试)
```

### 4.4 SSH 情况

```
~/.ssh/
├── id_ed25519          ← 当前主密钥 (已尝试但 1.8 拒绝了)
├── id_openclaw         ← 旧 Key (已废弃)
├── authorized_keys     ← 本机授权的公钥
├── config              ← SSH 配置 (只有 mi-pad 别名)
└── known_hosts         ← 没有 192.168.1.8 的记录

⚠️ 1.8 未配免密，不要反复尝试
⚠️ 不要扫 1.8 的其他端口，浪费时间
⚠️ 如果老大给了密码 → 用 sshpass 或 ssh-copy-id
```

### 4.5 已知 API 格式细节（很重要）

| 端点 | 响应格式 | 特殊说明 |
|------|---------|---------|
| `/api/health` | `{"success":true, "data":"..."}` | 标准包装 |
| `/api/status` | **直接返回结构体**（没有 success/data 包装） | 测试中注意区分 |
| 其他 `/api/v1/*` | `{"success":true, "data":..., "error":"<nil>"}` | `error` 字段 `<nil>` 是字符串不是 null |
| `task_id` 字段 | **不传则 Gateway 返回空字符串** | 提交任务时必须传 task_id，用 `test-$(date +%s)` 或 UUID |
| JSON 转义 | shell 直接 `curl -d '{}'` 容易出转义错 | **推荐用 Python requests 提交**，见 5.4 |

---

## 5. 故障排查链路

```
问题发现 ──→ 对照症状 → 跳到对应小节
                   ├─ 网关不通              → 5.1
                   ├─ Worker 不在线          → 5.2
                   ├─ 任务提交失败           → 5.3
                   ├─ JSON 转义失败          → 5.4
                   ├─ 任务执行错误           → 5.5
                   └─ 代码编译或更新失败      → 5.6
```

### 5.1 网关起不来 / 连不上

```bash
# 1. 检查进程
ps aux | grep computehub | grep -v grep

# 2. 检查端口
ss -tlnp | grep 8282

# 3. 检查端口冲突
ss -tlnp | grep -E "8282|18789"

# 4. 查看日志
# Gateway 日志输出到 stdout，可以重新启动看输出
cd /root/.openclaw/workspace/projects/computehub

# 5. 重启
./deploy/ubuntu/bin/computehub-gateway &

# 6. 确认
sleep 1
curl -s http://192.168.1.7:8282/api/health

# 如果端口被占用
kill <旧PID> && ./deploy/ubuntu/bin/computehub-gateway &
```

**常见原因：配置文件中 IP/端口写错，或旧进程挂了。**

### 5.2 Worker 不在线

```bash
# 1. 检查节点列表
curl -s http://192.168.1.7:8282/api/v1/nodes/list | python3 -m json.tool

# 2. 如果 cqf-worker-02 不在线：
#    → 它在 Windows 上运行，可能 Windows 那边 worker 进程掉了
#    → 问老大是否重启了 Windows / worker
#    → 或者等它自动重连（心跳间隔 10s）

# 3. 如果 cqf-worker-01 不在线（它从来没接通过）：
#    → 它在 192.168.1.8 上，连的是旧地址 192.168.1.4:8282
#    → 需要上去重配 worker 指向 192.168.1.7:8282
#    → ❌ 不要尝试用 SSH 反复连接（没免密）
#    → ✅ 问老大要密码，然后配免密后登录改配置

# 4. 注册一个临时节点验证 API 本身正常
curl -s -X POST http://192.168.1.7:8282/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_id":"diag-node","gpu_type":"CPU","region":"cn-east","max_tasks":2}' | python3 -m json.tool
```

### 5.3 任务提交失败

```bash
# 错误模式1: task_id 为空 → 手动传入
# ❌ curl -d '{"node_id":"cqf-worker-02","command":"echo hi"}'
# ✅ curl -d '{"task_id":"debug-001","node_id":"cqf-worker-02","command":"echo hi"}'

# 错误模式2: node_id 不存在（没指定或打错字）
# 任务会进入队列但永远没 Worker 认领

# 错误模式3: JSON 格式错误
# ❌ {command: "echo hi"}         (key没引号)
# ❌ '{"command":"echo && ver"}'  (shell 双引号嵌套错误)

# ✅ 正确测试：
TASK_ID="debug-$(date +%s)"
curl -s -X POST http://192.168.1.7:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d "{\"task_id\":\"$TASK_ID\",\"node_id\":\"cqf-worker-02\",\"command\":\"echo ok\"}"

# 或者用 Python（推荐，避免转义问题）
python3 -c "
import requests
r = requests.post('http://192.168.1.7:8282/api/v1/tasks/submit',
  json={'task_id':'debug-001','node_id':'cqf-worker-02','command':'echo ok'})
print(r.json())
"
```

### 5.4 JSON 转义错误（最常见问题）

**场景**：在 shell 中通过 `curl -d` 提交含中文、管道、引号的命令

```bash
# ❌ 错误示例：
curl -d '{"command":"echo 中文 && ver | findstr OS"}'  # shell 解析 `&&` 和 `|`

# ✅ 方案A: 用 Python 提交（推荐）
python3 << 'PYEOF'
import requests
r = requests.post("http://192.168.1.7:8282/api/v1/tasks/submit", json={
    "task_id": "py-001",
    "node_id": "cqf-worker-02",
    "command": "echo 中文测试 && ver && echo DONE",
    "timeout_seconds": 30
})
print(r.json())
PYEOF

# ✅ 方案B: 用文件存 JSON
echo '{"task_id":"f-001","node_id":"cqf-worker-02","command":"echo ok"}' > /tmp/task.json
curl -s -X POST -d @/tmp/task.json -H "Content-Type: application/json" \
  http://192.168.1.7:8282/api/v1/tasks/submit
```

### 5.5 任务执行错误

```bash
# 先查 detail 看 exit_code 和 stderr
curl -s "http://192.168.1.7:8282/api/v1/tasks/detail?task_id=<ID>&node_id=cqf-worker-02"

# 常见原因1: Linux 命令发到 Windows Worker 上了
#   - Windows 不认识 `uname`, `cat /proc/cpuinfo`, `&&`（要用 `&`）
#   - 解决方法：确认节点平台，用对应命令

# 常见原因2: 命令找不到
#   - exit_code=1, stderr="'xxx' 不是内部或外部命令"
#   - 解决方法：用全路径或在 Windows 上先 `where xxx` 确认

# 常见原因3: 超时
#   - 检查 timeout_seconds 是否设得太小（默认可能为 0 无限等待）
#   - 提交时带上 `"timeout_seconds": 30`

# 查询所有任务状态（包括历史的）
curl -s http://192.168.1.7:8282/api/v1/tasks/list | python3 -c "
import sys, json
d = json.load(sys.stdin)
for nid, tasks in d.get('data',{}).items():
    for t in tasks:
        print(f'{t.get(\"status\"):10s} | {t.get(\"command\",\"\")[:60]}')
"
```

### 5.6 代码编译失败 / 更新部署

```bash
# 编译（本机是 ARM64）
cd /root/.openclaw/workspace/projects/computehub
cargo build --release -p computehub-gateway 2>&1 | tail -20
cargo build --release -p computehub-worker 2>&1 | tail -20

# 编译产物位置
ls -la target/release/computehub-gateway 2>/dev/null
ls -la target/release/computehub-worker 2>/dev/null

# 部署（覆盖旧二进制）
cp target/release/computehub-gateway deploy/ubuntu/bin/
cp target/release/computehub-worker deploy/ubuntu/bin/

# ⚠️ 注意：deploy/ubuntu/bin/ 下的二进制是 ARM64
# ⚠️ 如果要在 192.168.1.8 (x86_64) 上跑，需要交叉编译给 x86_64
# ⚠️ 本机没法编译 x86_64 版本（除非装交叉工具链）

# 重启
kill <旧PID> && ./deploy/ubuntu/bin/computehub-gateway &
```

---

## 6. 修改代码后的验证流程

### 6.1 标准流程

```bash
# 1. 编辑代码
vim src/gateway/gateway.go

# 2. 编译
cargo build --release -p computehub-gateway 2>&1
# 如果编译失败 → 看最后几行错误信息，修完再试

# 3. 部署
cp target/release/computehub-gateway deploy/ubuntu/bin/

# 4. 重启
kill $(pgrep -f "computehub-gateway")
./deploy/ubuntu/bin/computehub-gateway &
sleep 1

# 5. 验证存活
curl -s http://192.168.1.7:8282/api/health

# 6. 跑测试
python3 tests/test_computehub.py

# 7. 对比结果
# 如果失败数 > 0，比上次（21/21）多 → 检查改了什么
git diff src/

# 8. 确认通过后 commit
git add -A
git commit -m "更新: <做了什么> - 测试全部通过 21/21"
```

### 6.2 回退

```bash
# 如果弄坏了
git checkout -- src/gateway/gateway.go

# 重新编译部署
cargo build --release -p computehub-gateway
cp target/release/computehub-gateway deploy/ubuntu/bin/
kill <PID> && ./deploy/ubuntu/bin/computehub-gateway &

# 验证
python3 tests/test_computehub.py
```

---

## 7. 历史错误记录 & 教训（必读）

```
🚨 以下错误反复出现过，接手 AI 必须读完再动手
🚨 不要重复踩这些坑
```

### E-001: SSH 反复尝试浪费时间
- **问题**: 知道 1.8 有 worker 但没密码，反复尝试不同密钥
- **耗时**: ~10 分钟
- **教训**: 确认没免密后，直接问老大密码，不要自己试
- **规范**: 尝试 1 次失败后 → 标记"需人工" → 跳到下一步

### E-002: 架构不匹配
- **问题**: 本机编译的 worker 是 ARM64，1.8 是 x86_64
- **耗时**: 编译 + 部署后发现跑不了
- **教训**: 在分发二进制前先确认目标架构
- **规范**: `file deploy/ubuntu/bin/computehub-worker` 检查，`uname -m` 确认目标

### E-003: JSON 转义反复出错
- **问题**: shell 里 `curl -d '{}'` 中嵌套 `&&` `|` 引号时解析错
- **耗时**: 反复提交→失败→改格式→再提交
- **教训**: 复杂命令用 Python requests 提交，不要用 shell 拼 JSON
- **规范**: 所有包含特殊字符的 command 用 Python 或 `-d @file.json`

### E-004: task_id 为空
- **问题**: 提交任务没传 task_id，Gateway 返回空字符串
- **后果**: 后续查 detail/progress 查不到
- **教训**: task_id 不是自动生成的，必须手动传
- **规范**: 生成规则 `test-$(date +%s)` 或 `uuidgen`，确保唯一

### E-005: 扫描无关 IP
- **问题**: 扫了一堆同网段设备的端口（1.7, 1.8, 1.4...）
- **耗时**: ~5 分钟
- **教训**: 固定网关地址 192.168.1.7:8282，不要扫
- **规范**: 只检查已知地址，不主动扫描

### E-006: Worker 连错 Gateway
- **问题**: cqf-worker-01 配置写死了 192.168.1.4:8282
- **后果**: Worker 运行中但连不上任何 Gateway
- **教训**: Worker 的 Gateway 地址可能硬编码在启动参数或配置里
- **规范**: 排查 Worker 为什么不在线时，先看它的日志里连的是哪个地址

### E-007: Windows vs Linux 命令混淆
- **问题**: 把 Linux 命令 `uname`, `cat /proc/cpuinfo` 发到 Windows Worker
- **后果**: exit_code=1，stderr 乱码（中文字符编码问题）
- **教训**: Worker 平台决定命令语法，Windows 用 `ver` 和 `wmic`
- **规范**: 提交前确认目标节点平台，用对应命令

### E-008: 重复探测已知信息
- **问题**: ping、端口扫描、系统信息查询，同一件事做了多遍
- **耗时**: ~15 分钟累积
- **教训**: 环境已固化在第 4 节，直接读就行
- **规范**: 接手后先读规范，不要自己从头探测

---

## 8. 已知测试偏差 / 未修复 BUG

| 偏差 | 预期行为 | 实际行为 | 原因 | 影响级别 |
|------|---------|---------|------|---------|
| 空 node_id 提交任务 | 应报错 | 成功入队列 | Gateway 不校验 node_id 必填 | ⚠️ 低（无 Worker 认领） |
| progress exit_code | 应返回 int | 返回 null | Worker 推送时没带 exit_code | ⚠️ 只影响 TUI |
| node metrics 需 node_id | 可不传参数 | 必须传 | API 设计如此 | ⚠️ 文档匹配 |
| active_tasks 显示 -1 | 应为 0 | 显示 -1 | NodeManager 初始化 bug | ⚠️ 显示问题，不影响功能 |
| /api/status 响应格式 | 标准 success/data 包装 | 直接裸返回结构体 | 历史遗留 | ⚠️ 测试已适配 |
| stderr 中文乱码 | 正常中文 | 乱码 | Windows 编码问题 | ⚠️ 仅窗口展示 |

**处理原则**:
- 不改测试去适配 bug → 应该修代码
- 如果决定修 → 修完跑全量测试确认
- 修完后更新此表

---

## 9. 测试脚本维护规范

### 9.1 新增功能
```python
# 1. 在文件底部写测试函数
def test_my_new_feature():
    ...

# 2. 注册到 TEST_GROUPS
TEST_GROUPS = {
    ...
    "myfeature": test_my_new_feature,
}

# 3. 在 run_all() 中注册
test_my_new_feature()

# 4. 跑全量确认
python3 tests/test_computehub.py
# 预期: 22/22 全部通过
```

### 9.2 修改测试
- 不改预期去适配代码 bug
- 如果测试有 bug（比如逻辑写错了），修完写明原因
- commit message 格式：`测试: <改动> - 原因`

### 9.3 运行纪律
- **每次 Gateway 代码变更后** → 跑全量
- **每次 Worker 代码变更后** → 跑全量
- **每次发现新 bug** → 要么修，要么加测试用例
- **commit 前** → 确认测试通过
- **上线前** → 跑一次

---

## 10. 快速诊断命令速查

```bash
# 看网关活了没
curl -s http://192.168.1.7:8282/api/health

# 看有哪些节点
curl -s http://192.168.1.7:8282/api/v1/nodes/list | python3 -m json.tool

# 看所有任务状态（最常用）
curl -s http://192.168.1.7:8282/api/v1/tasks/list | python3 -c "
import sys, json
d = json.load(sys.stdin)
for nid, tasks in d.get('data',{}).items():
    print(f'{nid}: {len(tasks)} tasks')
    for t in tasks:
        print(f'  {t[\"status\"]:10s} {t.get(\"command\",\"\")[:80]}')
"

# 查某个任务的结果
curl -s "http://192.168.1.7:8282/api/v1/tasks/detail?task_id=<ID>&node_id=<NODE>"

# 查流式输出
curl -s "http://192.168.1.7:8282/api/v1/tasks/progress?task_id=<ID>"

# 提交测试任务
python3 -c "
import requests
r = requests.post('http://192.168.1.7:8282/api/v1/tasks/submit', json={
    'task_id': 'diag-' + str(int(__import__(\"time\").time())),
    'node_id': 'cqf-worker-02',
    'command': 'echo ok && hostname',
    'timeout_seconds': 15
})
print(r.json())
"

# 重启 Gateway
kill <PID> && ./deploy/ubuntu/bin/computehub-gateway &

# 回退代码
git checkout -- src/gateway/gateway.go

# 看编译是否成功
cargo build --release -p computehub-gateway 2>&1 | tail -5
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-09 | 初始版，8节21项测试通过 |
| **v2.0** | **2026-05-09** | **全面重写：新增历史错误8条、诊断速查、代码结构、API清单、快速诊断速查、Windows/Linux区分、编译部署流程** |
