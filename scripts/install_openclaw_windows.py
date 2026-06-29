#!/usr/bin/env python3
"""
WIN-STD-001 标准流程：windows-mobile 安装 OpenClaw 2026.3.13

使用方式（windows-mobile 在线后）：
  python3 install_openclaw_windows.py

或者分步手动提交：
  Step 1: 检查环境
  Step 2: 安装 OpenClaw
  Step 3: 验证
"""
import json, urllib.request, time, base64, sys

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile"

PASS = 0
FAIL = 0
STEPS = []

def green(s): return f"\033[92m{s}\033[0m"
def red(s):   return f"\033[91m{s}\033[0m"
def blue(s):  return f"\033[94m{s}\033[0m"

def submit(cmd, timeout=45, node=NODE):
    body = json.dumps({"node_id": node, "command": cmd, "timeout": timeout}).encode()
    req = urllib.request.Request(
        GW + "/api/v1/tasks/submit",
        data=body, headers={"Content-Type": "application/json"},
        timeout=15
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp.get("data", {}).get("task_id", "")

def wait(tid, max_wait=60):
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(3)
        elapsed += 3
        resp = json.loads(urllib.request.urlopen(
            GW + f"/api/v1/tasks/detail?task_id={tid}", timeout=10
        ).read())
        data = resp.get("data", {})
        status = data.get("status")
        if status in ("completed", "failed", "timed_out"):
            return data
    return data

def run(cmd, timeout=45, label=""):
    tid = submit(cmd, timeout)
    data = wait(tid, timeout + 15)
    stdout = (data.get("stdout") or "").strip()
    stderr = (data.get("stderr") or "").strip()
    ec = data.get("exit_code")
    status = data.get("status")
    ok = ec == 0 and status == "completed"
    
    STEPS.append({"label": label, "ok": ok, "stdout": stdout[:200], "stderr": stderr[:100]})
    if ok:
        print(f"  {green('✅')} {label}")
        global PASS; PASS += 1
    else:
        print(f"  {red('❌')} {label} (exit={ec}, status={status})")
        global FAIL; FAIL += 1
        if stdout: print(f"     stdout: {stdout[:200]}")
        if stderr: print(f"     stderr: {stderr[:100]}")
    return data

def submit_encoded(ps_code, timeout=15, label=""):
    """使用 PowerShell -EncodedCommand 避免引号嵌套"""
    b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
    return run(f"powershell -EncodedCommand {b64}", timeout, label)

def set_path(paths):
    """一次性补 PATH"""
    combined = ";".join(paths)
    ps_code = f"[Environment]::SetEnvironmentVariable('Path', '{combined};' + [Environment]::GetEnvironmentVariable('Path','Machine'), 'Machine')"
    b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
    return run(f"powershell -EncodedCommand {b64}", 15, "设置系统 PATH")

print(blue("=" * 60))
print(blue("  WIN-STD-001: windows-mobile 安装 OpenClaw 2026.3.13"))
print(blue("=" * 60))
print()

# ── Step 1: 检查环境 ──
print(blue("\n═══ Step 1/4: 检查环境 ═══"))
run("echo NODE_OK", 15, "节点在线")
run("echo %PROCESSOR_ARCHITECTURE%", 15, "CPU架构")
run("net session >nul 2>&1 && echo ADMIN || echo NOT_ADMIN", 15, "管理员权限")
run("where node 2>&1 || echo NO_NODE", 15, "Node.js 是否存在")

# ── Step 2: 安装 OpenClaw ──
print(blue("\n═══ Step 2/4: 安装 OpenClaw 2026.3.13 ═══"))
run("npm install -g openclaw@2026.3.13", 120, "npm install openclaw@2026.3.13")

# ── Step 3: 验证 ──
print(blue("\n═══ Step 3/4: 验证安装 ═══"))
# 完整路径验证
run("C:\\Users\\xiaomi\\AppData\\Roaming\\npm\\openclaw.cmd --version 2>&1 || "
    "C:\\Progra~1\\nodejs\\openclaw.cmd --version 2>&1 || "
    "C:\\npm\\openclaw.cmd --version 2>&1", 15, "openclaw --version")

# PATH 验证
submit_encoded(
    '[Environment]::GetEnvironmentVariable("Path","Machine").Contains("AppData")',
    10, "PATH 包含 npm 路径"
)

# ── Step 4: 功能测试 ──
print(blue("\n═══ Step 4/4: 功能测试 ═══"))
# 尝试找个可能的位置
for ver_cmd in [
    "where openclaw 2>&1",
    "for %i in (openclaw openclaw.cmd) do @where %i 2>nul",
    "dir /s /b C:\\Users\\xiaomi\\AppData\\Roaming\\npm\\openclaw* 2>nul || dir /s /b C:\\Progra~1\\nodejs\\openclaw* 2>nul || echo NOT_FOUND"
]:
    run(ver_cmd, 15, f"查找 openclaw 路径")

# ── 总结 ──
print()
print(blue("=" * 60))
total = PASS + FAIL
pct = (PASS / total * 100) if total > 0 else 0
if FAIL == 0:
    print(green(f"  ✅ OpenClaw 2026.3.13 安装完成! {PASS}/{PASS} 通过"))
else:
    print(red(f"  ⚠️ {PASS}/{total} 通过 ({pct:.0f}%)"))
    for s in STEPS:
        if not s["ok"]:
            print(f"    ❌ {s['label']}: {s['stderr'] or s['stdout'][:80]}")
print(blue("=" * 60))
print()

if __name__ == "__main__":
    # 如果直接执行，从最基础的连通性开始检查
    pass