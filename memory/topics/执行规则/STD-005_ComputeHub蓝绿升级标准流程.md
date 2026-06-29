# STD-005: ComputeHub 蓝绿升级标准流程

> v1.1 · 2026-06-04 基于 ECS (linux/amd64) + windows-mobile 实战
> 
> **核心理念**: 旧Worker全程活着 → 新Gateway启动并全面测试通过 → 杀旧Worker释放文件锁 → 替换文件 → 启动新Worker

---

## 🏗️ 蓝绿升级全程

```
Before:  旧Worker(PID A) → 管理 旧Gateway(PID B, 8282)
              binary: computehub (旧)
```

### Step 1-2：准备

```
① copy 备份              旧Worker执行 → computehub → computehub.bak.旧版本号
② kill 旧Gateway         旧Worker执行 → kill PID B (释放8282端口)
```

### Step 3：启动新Gateway（蓝）

```
③ start 新Gateway        旧Worker执行 → start 新binary gateway
                                      新Gateway(PID C, 8282)
```

### Step 4：新Gateway全面功能测试 ⭐

```
④ 详细测试新Gateway       从外部或旧Worker通过8282全面测试
   ├─ GET /api/health         → 健康检查
   ├─ GET /api/v1/nodes/list  → 节点列表（含版本号）
   ├─ GET /api/v1/gallery     → Gallery 页面
   ├─ POST /api/v1/tasks/submit → 任务提交
   ├─ GET /api/v1/worker/health → Worker 连通性
   └─ POST /api/v1/agent/think  → AI 智能体
   │
   ├─ 全部通过 → ✅ 继续到Step 5
   └─ 有失败 → ❌ 回滚（旧Worker还在，恢复旧Gateway）
```

### Step 5-7：替换Worker

```
⑤ kill 旧Worker          （linux: kill / windows: taskkill）
⑥ 替换 binary            （linux: cp / windows: move）
⑦ start 新Worker         （新binary worker --gw ...）
                          新Worker(PID D) 注册到Gateway
```

### Step 8：清理

```
⑧ 清理临时文件          删除下载的临时binary、过期的备份
⑨ 验证节点版本号         nodes/list 显示新版本号
```

```
After:   新Worker(PID D) → 管理 新Gateway(PID C, 8282)
              binary: computehub (新)
              备份:  computehub.bak.v旧版本 (旧)
```

---

## 0️⃣ 前置条件

- [ ] 新 binary 已编译并上传到 ECS Gallery（`sync-deploy.sh` + Gallery 上传）
- [ ] deploy/version.txt 和 sha256sums 已更新
- [ ] ECS Gateway 在线（`/api/health` 返回正常）
- [ ] 所有目标 Worker 节点在线（`nodes/list` 显示 online）
- [ ] 确认各节点 Worker 的运行路径（Linux: `/usr/local/bin/computehub` 或 `/home/computehub/computehub`；Windows: `C:\Windows\System32\computehub.exe` 或 `C:\tmp\computehub.exe`）
- [ ] 确认代码里 `HeartbeatReq` 结构体有 `Version` 字段（v1.3.11+ 自带，旧版需检查）

### 查当前 PID（Linux ECS）

```bash
# ECS 直接查
ps aux | grep computehub | grep -v grep
# 或
pgrep -af computehub
```

### 查当前 PID（Windows 节点）

```python
import base64, json, urllib.request, time

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile"

def ps(cmd):
    return f"powershell -EncodedCommand {base64.b64encode(cmd.encode('utf-16le')).decode()}"

def submit(cmd, timeout=10, node=NODE):
    body = {"command": cmd, "timeout": timeout, "priority": 10}
    body["assigned_node"] = node
    req = urllib.request.Request(GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read()).get("data",{}).get("task_id","")

def poll(tid, max_wait=15):
    for i in range(max_wait):
        time.sleep(1)
        resp = json.loads(urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") in ("completed", "failed"): return d
    return None

# 查 Worker PID (port 8383)
tid = submit(ps("(Get-NetTCPConnection -LocalPort 8383).OwningProcess"), 10)
d = poll(tid, 12)
worker_pid = [l.strip() for l in (d.get('stdout') or '').split('\n') if l.strip().isdigit()][0]
print(f"Worker PID: {worker_pid}")

# 查 Worker 路径
tid = submit(ps(f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {worker_pid}').ExecutablePath"), 10)
d = poll(tid, 12)
exe_path = (d.get('stdout') or '').strip()
print(f"Worker EXE: {exe_path}")
```

---

## 1️⃣ 下载新 binary

### Linux ECS

```bash
# 从部署机 scp 到 ECS
scp -P 8022 -i ~/.ssh/id_ed25519_computehub \
  bin/linux-amd64/computehub \
  computehub@36.250.122.43:/home/computehub/computehub.v1.3.11
```

### Windows 节点（通过 Task 下载）

```python
print("⬇️  下载新 binary...")
tid = submit(
    f'cmd /c curl -sL -o C:\\Windows\\System32\\computehub.new.exe '
    f'http://36.250.122.43:8282/api/v1/files/computehub-windows-amd64.exe & echo DL_OK',
    60
)
d = poll(tid, 65)
assert 'DL_OK' in (d.get('stdout') or ''), "下载失败"
print("   ✅")
```

---

## 2️⃣ 第一阶段：Gateway 蓝绿切换

### Windows 节点（Worker 提 Gateway 升级）

```python
print("📦 Step 1-3: 备份→杀旧Gateway→启动新Gateway...")
phase1 = (
    'cmd /c '
    f'copy /Y C:\\Windows\\System32\\computehub.exe C:\\Windows\\System32\\computehub.old.exe >nul & '
    f'taskkill /f /pid {gw_pid} >nul 2>&1 & '
    f'start /B C:\\Windows\\System32\\computehub.new.exe gateway & '
    f'echo PHASE1_DONE'
)
tid = submit(phase1, 15)
d = poll(tid, 18)
time.sleep(3)
```

### Linux ECS（SSH 直连）

```bash
# 备份旧 binary
cp /home/computehub/computehub /home/computehub/computehub.bak.v1.3.10

# 替换为新 binary
rm /home/computehub/computehub
cp /home/computehub/computehub.v1.3.11 /home/computehub/computehub
chmod +x /home/computehub/computehub

# Kill 旧 Gateway
kill -9 <OLD_GW_PID>

# 启动新 Gateway
cd /home/computehub
nohup ./computehub gateway > /tmp/gateway.log 2>&1 &

# 验证新版本
./computehub version
# → ComputeHub v1.3.11
```

> ⚠️ **注意**: `cp` 覆盖正在运行的可执行文件会报 `Text file busy`。必须先 kill 旧进程再替换。

---

## 3️⃣ 第二阶段：新Gateway全面功能测试 ⭐（核心步骤）

```python
print("\n🔬 Step 4: 新Gateway全面功能测试...")
test_results = {}
all_pass = True

def _test(name, cmd, check_fn, node=None):
    global all_pass
    tid = submit(cmd, 10, node)
    d = poll(tid, 12)
    out = (d.get('stdout') or '').strip()
    ok = check_fn(out)
    print(f"  {'✅' if ok else '❌'} {name}")
    if not ok: all_pass = False

# 测试1: Health API
_test("Health API", 'curl -s http://localhost:8282/api/health',
      lambda o: '"success":true' in o)

# 测试2: 节点列表（检查版本号是否显示）
_test("Nodes API", 'curl -s http://localhost:8282/api/v1/nodes/list',
      lambda o: '"success":true' in o and 'node_id' in o)

# 测试3: Gallery
_test("Gallery", 'curl -s -o NUL -w "%{http_code}" http://localhost:8282/',
      lambda o: '200' in o)

# 测试4: 任务提交
_test("Task Submit", 'echo hello_from_new_gw',
      lambda o: 'hello_from_new_gw' in o)

# 测试5: Worker 连通性（旧Worker仍活着）
_test("Worker Health", 'curl -s http://localhost:8383/api/v1/worker/health',
      lambda o: '"status":"ok"' in o)

# 决定
print(f"\n  总体判定: {'✅ 全部通过，继续升级' if all_pass else '❌ 有失败项，执行回滚'}")
if not all_pass:
    print("\n🔄 执行回滚...")
    # 恢复旧 Gateway
    # 略
    exit(1)
```

---

## 4️⃣ 第三阶段：Worker 切换（蓝→绿）

### Linux ECS

```bash
# ⑤ Kill 旧 Worker
kill <OLD_WORKER_PID>

# ⑥ 替换 binary（已经替换过，不需要重复）
# cp /home/computehub/computehub.v1.3.11 /home/computehub/computehub

# ⑦ 启动新 Worker
nohup /home/computehub/computehub worker \
  --gateway http://localhost:8282 \
  --node-id ecs-p2ph \
  --region cn-east \
  > /tmp/worker.log 2>&1 &

# 验证
curl -s http://localhost:8383/api/v1/worker/health
# → {"node_id":"ecs-p2ph","status":"ok"}
```

### Windows 节点（通过 Task 提交）

```python
print("\n🔄 Step 5-7: 杀旧Worker→替换文件→启动新Worker...")

# ⚠️ 关键：taskkill 会杀掉执行命令的 Worker 进程！
# 正确做法：先用 schtasks 调度延迟执行，让当前任务先安全返回
# 参考 WIN-COM-002 Base64 传输标准

phase3 = (
    f'schtasks /CREATE /SC ONCE /TN "ComputeHubUpgrade" /ST 23:59 /TR '
    f'"cmd.exe /c \\"'
    f'timeout /T 15 /NOBREAK & '
    f'curl -s -o C:\\\\Windows\\\\System32\\\\computehub.new.exe '
    f'http://36.250.122.43:8282/api/v1/files/computehub-windows-amd64.exe & '
    f'taskkill /F /IM computehub.exe /T & '
    f'timeout /T 3 /NOBREAK & '
    f'move /Y C:\\\\Windows\\\\System32\\\\computehub.new.exe '
    f'C:\\\\Windows\\\\System32\\\\computehub.exe & '
    f'start /B C:\\\\Windows\\\\System32\\\\computehub.exe worker '
    f'--gw http://36.250.122.43:8282 --node-id windows-mobile '
    f'--interval 3 --concurrent 4 --heartbeat 10 & '
    f'schtasks /DELETE /TN ComputeHubUpgrade /F'
    f'\\"" '
    f'/F 2>&1 & echo SCHEDULE_DONE'
)
```

---

## 5️⃣ 第四阶段：验证升级结果

```python
print("\n⏳ 等 15 秒让新Worker注册...")
time.sleep(15)

print("\n🔍 Step 验证: 检查升级结果...")

import urllib.request, json
r = json.loads(urllib.request.urlopen(f"{GW}/api/v1/nodes/list", timeout=10).read())
for node in r.get("data", []):
    v = node.get('version', '')
    print(f"  📌 {node['node_id']:25s} {node['status']:10s} v={v if v else '(空 — 旧版本问题)'}")
    if node['status'] == 'online' and v != '':
        print(f"  ✅ {node['node_id']} 升级成功！版本 v{v}")
```

### 版本号验证标准

| 状态 | 含义 | 原因 |
|------|------|------|
| `v='1.3.11'` | ✅ 正常 | 新版心跳带了版本号 |
| `v='1.3.10'` | ✅ 正常（旧版） | 旧 binary 还在跑 |
| `v=''` | ⚠️ 版本号丢失 | `HeartbeatReq` 缺 `Version` 字段（旧代码bug），或 Gateway 重启后心跳自动注册没带版本 |
| **offline** | ❌ 升级中断 | Worker 被自杀或网络问题 |

---

## 6️⃣ 🚨 常见陷阱与避坑指南

### 陷阱 1：Worker 自杀升级（本次实战踩坑）

```diff
- ❌ 提交 taskkill /F /IM computehub.exe
    → 杀的是执行任务命令的 Worker 进程本身
    → 任务结果永远 pending/running
    → Worker offline，需要手动重启

+ ✅ 用 schtasks 延迟执行
    → 当前任务先返回 completed
    → schtasks 30秒后独立执行下载+替换+启动
```

**正确做法**：先用 schtasks 写一个延迟任务，让升级命令在当前 Worker 进程之外执行。

### 陷阱 2：Windows 运行路径不一致

```diff
- ❌ 以为 Worker 在 C:\tmp\computehub.exe
    → 实际运行在 C:\Windows\System32\computehub.exe
    → move 替换了错误位置的文件，升级无效

+ ✅ 升级前先查 Worker 的实际路径
    → wmic process where "name='computehub.exe'" get ExecutablePath
    → 或: (Get-Process computehub).Path
```

### 陷阱 3：Linux `Text file busy`

当你试图 `cp` 覆盖正在运行的可执行文件：
```bash
cp computehub.v1.3.11 /usr/local/bin/computeub
# cp: cannot create regular file '/usr/local/bin/computehub': Text file busy
```
必须先 kill 旧进程，再替换，再启动。

### 陷阱 4：Gateway 重启后版本号丢失

`HeartbeatReq` 结构体缺 `Version` 字段 → 心跳自动注册时版本号为空 → nodes/list 显示 `v=''`

**修复**（已合入 v1.3.11+）：
```go
// src/workercmd/worker_main.go
type HeartbeatReq struct {
    NodeID         string  `json:"node_id"`
    GPUUtilization float64 `json:"gpu_utilization"`
    // ... 
    Version       string  `json:"version,omitempty"`  // ← 加上这个
}

// 心跳体传版本号
body, _ := json.Marshal(HeartbeatReq{
    NodeID:  s.nodeID,
    Version: version.Short(),  // ← 加上这个
    // ...
})
```

```go
// src/kernel/kernel.go — 心跳处理函数
// 心跳时读版本号，自动注册和更新都用它
hbVersion, _ := p["version"].(string)
```

### 陷阱 5：Gateway 重复进程（ECS kill 错进程）

```diff
- ❌ kill 掉的是实际在服务的 Gateway 进程
    → 服务中断，需要手动重启

+ ✅ 先验证要 kill 的 PID
    → pgrep -af 'computehub gateway'
    → 确认哪个是当前服务中的
```

---

## 7️⃣ 🚨 为什么必须杀Worker再move（关键理解）

```diff
- ❌ 旧Worker活着时 move 文件
    → Windows 拒绝覆盖正在运行的可执行文件
    → "访问被拒绝" / "文件被占用"

+ ✅ 先杀Worker再 move 文件
    → 文件锁释放
    → move 成功
```

**正确的依赖关系：**

```
kill旧Worker → 释放文件锁 → move替换成功 → 启动新Worker
    ⑤               等待           ⑥             ⑦
```

---

## 8️⃣ 升级状态流程图

```
                     ┌──────────────┐
                     │   旧体系运行中  │
                     │ Worker + GW   │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ ① copy备份    │
                     │ ② kill旧GW    │
                     │ ③ start新GW   │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ ④ 全面测试    │
                     │ 新Gateway     │
                     └──────┬───────┘
                            │
               ┌────────────┼────────────┐
               │ 全部通过    │            │ 有失败
               ▼            │            ▼
        ┌──────────────┐    │    ┌──────────────┐
        │ ⑤ kill旧Worker│    │    │ 回滚恢复     │
        │ ⑥ 替换binary │    │    │ 旧Gateway    │
        │ ⑦ start新Worker│   │    └──────────────┘
        └──────┬───────┘    │
               │            │
        ┌──────▼───────┐    │
        │ ⑧ 验证 ✅    │    │
        └──────────────┘    │
                            │
                     ┌──────▼───────┐
                     │ ⑨ 版本号检查 │
                     └──────────────┘
```

---

## 📜 实战验证（2026-06-04 蓝绿升级记录）

| Step | 操作 | ECS (linux/amd64) | windows-home-01 | windows-mobile |
|------|------|-------------------|-----------------|----------------|
| ① | 备份 | ✅ `computehub.bak.v1.3.10` | — | — |
| ② | kill 旧GW | ✅ kill 75089 | — | — |
| ③ | start 新GW | ✅ v1.3.11, 8282响应 | — | — |
| ④ | **全面测试** | ✅ Health/Gallery/Task/Worker | — | — |
| ⑤ | kill 旧Worker | ✅ kill 75090 | ✅ task completed | ❌ `taskkill` 自杀 |
| ⑥ | 替换 binary | ✅ cp (已在Step2完成) | ✅ | ❌ |
| ⑦ | start 新Worker | ✅ v1.3.11, 8383健康 | ✅ | ❌ offline |
| ⑧ | 验证版本号 | ✅ v1.3.11 | ⚠️ v1.3.10 | ⚠️ offline |

### 根因分析

| 问题 | 根因 | 修复 |
|------|------|------|
| windows-mobile 升级失败 | `taskkill /F /IM computehub.exe` 杀了执行任务的 Worker 自身 | 用 `schtasks` 延迟执行 |
| 版本号显示为空 | `HeartbeatReq` 缺 `Version` 字段 | `worker_main.go` + `kernel.go` 修复，v1.3.11+ |
| Gateway 重复进程 | nohup 没清理旧 n 伪进程 | 先 `pkill` 再启动 |
| `Text file busy` | 覆盖正在运行的文件 | 先 kill 进程再 cp |

---

## 9️⃣ 完整升级脚本（Python）

```python
#!/usr/bin/env python3
"""ComputeHub 蓝绿升级脚本"""
import base64, json, urllib.request, time, sys

GW = "http://36.250.122.43:8282"
NODE = "ecs-p2ph"  # Linux节点

def main():
    print("🚀 ComputeHub 蓝绿升级")
    
    # 前置：确认旧Worker在线
    r = json.loads(urllib.request.urlopen(f"{GW}/api/v1/nodes/list").read())
    for n in r.get("data", []):
        if n["node_id"] == NODE:
            print(f"📌 旧 {NODE}: {n['status']} v={n.get('version','?')}")
            assert n["status"] == "online", "节点不在线"
    
    # Phase 1: Gateway 切换（SSH 操作，需手动执行）
    print("⚠️  Phase 1 (Gateway): 需 SSH 到 ECS 执行")
    print("   ssh ecs-video")
    print("   cp computehub computehub.bak")
    print("   rm computehub; cp computehub.v1.3.11 computehub")
    print("   pkill -f 'computehub gateway'; nohup ./computehub gateway &")
    
    # Phase 2: 测试新Gateway
    print("\n🔬 Phase 2: 测试新Gateway...")
    # curl 各端点...
    
    # Phase 3: Worker 切换（Task 提交）
    print("\n🔄 Phase 3: Worker 切换...")
    # 对 Linux Worker 直接 kill → start
    # 对 Windows Worker 用 schtasks 延迟执行
    
    # Phase 4: 验证
    time.sleep(15)
    r = json.loads(urllib.request.urlopen(f"{GW}/api/v1/nodes/list").read())
    for n in r.get("data", []):
        if n["node_id"] == NODE:
            print(f"📌 {NODE}: {n['status']} v={n.get('version','?')}")

if __name__ == "__main__":
    main()
```

---

## 📦 相关文档

| 文档 | 内容 |
|------|------|
| WIN-UPG-002 | Windows 远程升级标准流程 |
| WIN-COM-002 | Base64 绕过 JSON 转义传输标准 |
| STD-004 | ComputeHub 版本升级发布标准流程 |
| WIN-PROC-001 | Windows 进程管理标准流程 |

---

**变更记录**

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-03 | v1.0 | 初版，基于 windows-home-01 实战 |
| 2026-06-04 | v1.1 | 新增 Linux ECS 流程、版本号修复、常见陷阱（Worker自杀/路径不一致/Text file busy/Gateway重启版本丢失） |