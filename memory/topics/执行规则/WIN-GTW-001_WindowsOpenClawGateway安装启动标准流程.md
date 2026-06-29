# WIN-GTW-001: Windows OpenClaw Gateway 安装与启动标准流程

> 建立时间: 2026-06-22
> 版本: v1.0
> 适用场景: 通过 ComputeHub Worker 远程安装/启动 Windows 节点的 OpenClaw Gateway
> 实战验证: windows-mobile01 (Windows 10 LTSC 2019, OpenClaw 2026.6.8)

---

## 目录

1. [前置检查](#1-前置检查)
2. [安装流程](#2-安装流程)
3. [启动流程](#3-启动流程)
4. [验证流程](#4-验证流程)
5. [常见问题与预案](#5-常见问题与预案)
6. [附录：命令速查](#6-附录命令速查)

---

## 1. 前置检查

### □ 1.1 确认 OpenClaw 已安装

```python
import json, urllib.request, time

GW = "http://<gateway>:8282"  # ComputeHub Gateway 地址

def submit(cmd, timeout=30, node="windows-mobile01"):
    body = {"command": cmd, "timeout": timeout, "priority": 8, "node_id": node}
    req = urllib.request.Request(
        GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data", {}).get("task_id", "")

def wait(tid, max_wait=30):
    for _ in range(max_wait // 3):
        time.sleep(3)
        resp = json.loads(urllib.request.urlopen(
            f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") == "completed":
            return d
    return {}

# 检查 openclaw 是否已安装
tid = submit('cmd.exe /c "openclaw --version 2>nul || echo NOT_INSTALLED"', 10)
d = wait(tid)
stdout = (d.get("stdout") or "").strip()
if "NOT_INSTALLED" in stdout:
    print("❌ OpenClaw 未安装，先走 WIN-STD-001 安装 Node.js + npm install -g openclaw")
else:
    print(f"✅ OpenClaw 已安装: {stdout[:100]}")
```

### □ 1.2 确认 .bat 文件路径

OpenClaw 安装后会在 `C:\Windows\system32\` 创建 `openclaw.bat`：

```batch
@echo off
node "C:\Windows\system32\config\systemprofile\AppData\Roaming\npm\node_modules\openclaw\openclaw.mjs" %*
```

**验证方法**:
```python
tid = submit('cmd.exe /c "type C:\\Windows\\system32\\openclaw.bat"', 10)
d = wait(tid)
# 预期输出包含 openclaw.mjs 路径
```

### □ 1.3 确认 Gateway 未运行

```python
tid = submit('netstat -ano | findstr 18789', 10)
d = wait(tid)
stdout = (d.get("stdout") or "").strip()
if stdout:
    print("⚠️ Gateway 已在运行，跳过安装")
else:
    print("✅ Gateway 未运行，可以安装")
```

---

## 2. 安装流程

### 2.1 核心命令

```python
# 通过 wmic 创建独立进程执行 gateway install
node_exe = "C:\\Progra~1\\nodejs\\node.exe"
mjs_path = "C:\\Windows\\system32\\config\\systemprofile\\AppData\\Roaming\\npm\\node_modules\\openclaw\\openclaw.mjs"

tid = submit(
    f'wmic process call create "{node_exe} {mjs_path} gateway install"',
    timeout=30
)
d = wait(tid, max_wait=30)
stdout = (d.get("stdout") or "").strip()
```

**预期输出**:
```
Executing (Win32_Process)->Create()
Method execution successful.
Out Parameters:
instance of __PARAMETERS
{
	ProcessId = <PID>;
	ReturnValue = 0;
};
```

**ReturnValue = 0** → 安装进程已启动 ✅

### 2.2 安装后等待

`gateway install` 会：
1. 创建 Windows 计划任务（schtasks）
2. 自动启动 Gateway 服务
3. 监听 `0.0.0.0:18789`

安装后等待 **10-15 秒**让 Gateway 完成启动。

### 2.3 为什么不直接用 `openclaw gateway start`

| 方法 | 结果 | 原因 |
|------|------|------|
| `openclaw gateway start` | ❌ 进程立即退出 | 提示 "Gateway service missing. Start with: openclaw gateway install" |
| `cmd /c "node.exe openclaw.mjs gateway start"` | ❌ 进程退出 | 同上，必须先 install |
| `wmic process call create "node.exe openclaw.mjs gateway install"` | ✅ 成功 | 安装服务后自动启动 |

**结论**: **必须先 `gateway install`，再 `gateway start` 或让 install 自动启动。**

---

## 3. 启动流程

### 3.1 安装后自动启动

`gateway install` 成功后 Gateway 会自动启动。验证即可。

### 3.2 手动启动（如果 install 后未自动启动）

```python
# 方案 A：wmic 创建独立进程（推荐）
tid = submit(
    f'wmic process call create "{node_exe} {mjs_path} gateway start"',
    timeout=15
)
d = wait(tid, max_wait=15)

# 方案 B：schtasks 运行已安装的服务
tid = submit(
    'cmd.exe /c "schtasks /Run /TN \\\"OpenClaw Gateway\\\" 2>&1 & echo DONE"',
    timeout=15
)
d = wait(tid, max_wait=15)
```

### 3.3 为什么用 wmic 而不是 cmd

| 方法 | 效果 | 推荐度 |
|------|------|--------|
| `wmic process call create "..."` | 创建独立进程，不阻塞任务 | ⭐ 推荐 |
| `cmd /c "..."` | 进程在任务 shell 内运行，退出后子进程可能被杀 | ❌ 不推荐 |
| `schtasks /Run` | 通过计划任务运行，独立于当前 shell | ✅ 备选 |

**wmic 优势**:
- 进程完全独立，任务完成退出后进程继续运行
- 不需要处理 cmd 引号嵌套
- 返回 PID 方便后续追踪

---

## 4. 验证流程

### 4.1 端口验证

```python
tid = submit('netstat -ano | findstr 18789', 10)
d = wait(tid)
stdout = (d.get("stdout") or "").strip()
# 预期: TCP    0.0.0.0:18789          0.0.0.0:0              LISTENING       <PID>
```

### 4.2 进程验证

```python
tid = submit('tasklist /FI "PID eq <PID>" /FO CSV', 10)
d = wait(tid)
# 预期: "node.exe","<PID>","Console","1","<MEM> K"
```

### 4.3 健康检查

```python
tid = submit('curl.exe -s http://127.0.0.1:18789/health', 10)
d = wait(tid)
stdout = (d.get("stdout") or "").strip()
# 预期: {"ok":true,"status":"live"}
```

### 4.4 完整验证脚本

```python
def verify_gateway(node="windows-mobile01"):
    checks = [
        ("端口监听", f'netstat -ano | findstr 18789'),
        ("健康检查", 'curl.exe -s http://127.0.0.1:18789/health'),
    ]
    results = {}
    for label, cmd in checks:
        tid = submit(cmd, 10, node)
        d = wait(tid, max_wait=10)
        out = (d.get("stdout") or "").strip()
        results[label] = out
        if "LISTENING" in out or '"ok":true' in out:
            print(f"  ✅ {label}: OK")
        else:
            print(f"  ❌ {label}: {out[:100]}")
    return all("LISTENING" in v or '"ok":true' in v for v in results.values())
```

---

## 5. 常见问题与预案

### ❌ Q1: `openclaw gateway start` 提示 "Gateway service missing"

**现象**: 运行 `openclaw gateway start` 后进程立即退出，提示需要先 install

**根因**: Gateway 服务未安装（计划任务不存在）

**解决**:
```python
# 必须先 install
tid = submit(f'wmic process call create "{node_exe} {mjs_path} gateway install"', 30)
```

**预防**: 安装前检查 `schtasks /Query /TN "OpenClaw Gateway" 2>nul`

### ❌ Q2: schtasks /Create 报 "Invalid argument/option"

**现象**: `schtasks /Create /SC ONCE /TN OpenClawGateway /TR "..." /ST 00:00 /F` 报错

**根因**: 路径中的空格被 schtasks 解析为多个参数

**解决**: 改用 wmic 创建进程，或确保路径用 8.3 短名

**预防**: 优先用 wmic，不用 schtasks 创建一次性任务

### ❌ Q3: 进程启动后立即退出

**现象**: wmic 返回 PID，但几秒后进程消失

**根因**: `openclaw gateway start` 在没有已安装服务的情况下会立即退出

**解决**: 先 `gateway install` 再验证

**预防**: 安装前确认 `openclaw --version` 返回版本号

### ❌ Q4: 端口 18789 被占用

**现象**: `netstat -ano | findstr 18789` 显示其他 PID

**解决**:
```python
# 查占用进程
tid = submit('netstat -ano | findstr 18789', 10)
# 杀旧进程
tid = submit('taskkill /F /PID <old_pid>', 10)
# 重新安装/启动
```

### ❌ Q5: 健康检查返回非 200

**现象**: `curl.exe -s http://127.0.0.1:18789/health` 超时或返回空

**根因**: Gateway 启动中、端口未监听、或进程崩溃

**解决**:
```python
# 等 5-10 秒再试
time.sleep(10)
# 检查进程
tid = submit('tasklist /FI "IMAGENAME eq node.exe" /FO CSV', 10)
# 检查端口
tid = submit('netstat -ano | findstr 18789', 10)
```

---

## 6. 附录：命令速查

### 6.1 关键路径

| 项目 | 路径 |
|------|------|
| openclaw.bat | `C:\Windows\system32\openclaw.bat` |
| openclaw.mjs | `C:\Windows\system32\config\systemprofile\AppData\Roaming\npm\node_modules\openclaw\openclaw.mjs` |
| node.exe | `C:\Program Files\nodejs\node.exe` (或 `C:\Progra~1\nodejs\node.exe`) |
| npm 全局模块 | `C:\Windows\system32\config\systemprofile\AppData\Roaming\npm\node_modules\` |

### 6.2 命令速查

```batch
rem 检查安装
openclaw --version

rem 查看 .bat 内容
type C:\Windows\system32\openclaw.bat

rem 安装 Gateway 服务
wmic process call create "C:\Progra~1\nodejs\node.exe C:\Windows\system32\config\systemprofile\AppData\Roaming\npm\node_modules\openclaw\openclaw.mjs gateway install"

rem 启动 Gateway
wmic process call create "C:\Progra~1\nodejs\node.exe C:\Windows\system32\config\systemprofile\AppData\Roaming\npm\node_modules\openclaw\openclaw.mjs gateway start"

rem 验证端口
netstat -ano | findstr 18789

rem 验证进程
tasklist /FI "PID eq <PID>" /FO CSV

rem 健康检查
curl.exe -s http://127.0.0.1:18789/health

rem 查看计划任务
schtasks /Query /TN "OpenClaw Gateway" /V /FO LIST 2>nul
```

### 6.3 Python 一键安装脚本

```python
"""WIN-GTW-001: Windows OpenClaw Gateway 一键安装"""
import json, urllib.request, time

GW = "http://<gateway>:8282"
NODE = "windows-mobile01"

def submit(cmd, timeout=30):
    body = {"command": cmd, "timeout": timeout, "priority": 8, "node_id": NODE}
    req = urllib.request.Request(
        GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data", {}).get("task_id", "")

def wait(tid, max_wait=30):
    for _ in range(max_wait // 3):
        time.sleep(3)
        resp = json.loads(urllib.request.urlopen(
            f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") == "completed":
            return d
    return {}

def install_gateway():
    print("🔍 检查 OpenClaw 安装...")
    tid = submit('cmd.exe /c "openclaw --version 2>nul || echo NOT_INSTALLED"', 10)
    d = wait(tid)
    out = (d.get("stdout") or "").strip()
    if "NOT_INSTALLED" in out:
        print("❌ OpenClaw 未安装，请先安装")
        return False
    print(f"✅ OpenClaw: {out[:80]}")
    
    print("🔍 检查 Gateway 状态...")
    tid = submit('netstat -ano | findstr 18789', 10)
    d = wait(tid)
    if (d.get("stdout") or "").strip():
        print("✅ Gateway 已在运行")
        return True
    
    print("📦 安装 Gateway 服务...")
    node_exe = "C:\\Progra~1\\nodejs\\node.exe"
    mjs = "C:\\Windows\\system32\\config\\systemprofile\\AppData\\Roaming\\npm\\node_modules\\openclaw\\openclaw.mjs"
    tid = submit(f'wmic process call create "{node_exe} {mjs} gateway install"', 30)
    d = wait(tid, max_wait=30)
    out = (d.get("stdout") or "").strip()
    if "ReturnValue = 0" not in out:
        print(f"❌ 安装失败: {out[:200]}")
        return False
    print("✅ 安装进程已启动")
    
    print("⏳ 等待 Gateway 启动...")
    time.sleep(15)
    
    print("🔍 验证端口...")
    tid = submit('netstat -ano | findstr 18789', 10)
    d = wait(tid)
    out = (d.get("stdout") or "").strip()
    if "LISTENING" not in out:
        print(f"❌ 端口未监听: {out[:200]}")
        return False
    print(f"✅ 端口: {out[:100]}")
    
    print("🔍 健康检查...")
    tid = submit('curl.exe -s http://127.0.0.1:18789/health', 10)
    d = wait(tid)
    out = (d.get("stdout") or "").strip()
    if '"ok":true' not in out:
        print(f"❌ 健康检查失败: {out[:200]}")
        return False
    print(f"✅ 健康: {out}")
    
    print("\n🎉 Windows OpenClaw Gateway 安装完成!")
    return True

install_gateway()
```

---

## 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-22 | v1.0 | 初版，基于 windows-mobile01 实战经验 |
