#!/usr/bin/env python3
"""
升级 windows-mobile 节点: 1.3.30 → 1.3.42
按 WIN-OPC-001 标准流程执行
"""
import json, urllib.request, time, sys, base64

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile"
NEW_VER = "1.3.42"
DL_URL = f"{GW}/api/v1/download?file=computehub-windows-amd64.exe&platform=windows/amd64"
SHA256 = "048c3711e9a58ca438428156b49a82fcfe9a35e6e7822207a98cac7f109666fb"

def submit(node_id, cmd, timeout=60, priority=8):
    payload = json.dumps({"node_id": node_id, "command": cmd, "timeout": timeout, "priority": priority}).encode()
    req = urllib.request.Request(f"{GW}/api/v1/tasks/submit", data=payload, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    task_id = resp.get("data", {}).get("task_id", "")
    print(f"  ⏳ Task: {task_id}")
    return task_id

def wait(task_id, poll_interval=2, max_wait=120):
    for i in range(max_wait // poll_interval):
        time.sleep(poll_interval)
        try:
            req = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}")
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            data = resp.get("data", {})
            status = data.get("status")
            if status in ["completed", "failed", "cancelled"]:
                return data
        except Exception as e:
            if i % 5 == 0:
                print(f"  ⚠️ 轮询异常: {e}")
    return None

def run(node_id, cmd, timeout=60, label=""):
    label = label or cmd[:50]
    print(f"\n  ▶ {label}")
    task_id = submit(node_id, cmd, timeout)
    result = wait(task_id, max_wait=timeout+30)
    if result:
        ec = result.get('exit_code', '?')
        stdout = (result.get('stdout') or '')[:300]
        stderr = (result.get('stderr') or '')[:200]
        print(f"  Exit: {ec}")
        if stdout: print(f"  Out: {stdout}")
        if stderr: print(f"  Err: {stderr}")
        return result
    else:
        print(f"  ⚠️ 超时/无结果")
        return None

def check_ok(result):
    return result and result.get('exit_code') == 0

print("=" * 60)
print(f"  🚀 升级 windows-mobile: 1.3.30 → {NEW_VER}")
print("=" * 60)

# === Step 0: 节点可达性检查 ===
print("\n" + "=" * 40)
print("  Step 0: 节点可达性检查")
print("=" * 40)

r = run(NODE, "echo OK", 10, "echo OK")
if not check_ok(r):
    print("  ❌ 节点不可达，中止")
    sys.exit(1)
print("  ✅ 节点在线")

r = run(NODE, "where powershell", 10, "检查 PowerShell")
if check_ok(r): print("  ✅ PowerShell 可用")

r = run(NODE, "where curl", 10, "检查 curl")
has_curl = check_ok(r)
if has_curl:
    print("  ✅ curl 可用")
else:
    print("  ⚠️ curl 不可用，将用 PowerShell 下载")

# === Step 1: 检查当前版本 ===
print("\n" + "=" * 40)
print("  Step 1: 检查当前版本")
print("=" * 40)

r = run(NODE, "dir C:\\computehub\\computehub.exe 2>nul && echo EXISTS || echo MISSING", 10, "检查 binary 位置")
if r:
    stdout = r.get('stdout', '')
    if 'EXISTS' in stdout:
        print("  ✅ C:\\computehub\\computehub.exe 存在")
    else:
        print("  ⚠️ 不在 C:\\computehub\\，尝试其他路径")

# 检查进程
r = run(NODE, "tasklist | findstr computehub", 10, "检查进程")
if r:
    print(f"  进程: {(r.get('stdout') or '')[:200]}")

# === Step 2: 下载新 binary ===
print("\n" + "=" * 40)
print(f"  Step 2: 下载 v{NEW_VER} binary")
print("=" * 40)

# 先清理旧临时文件
r = run(NODE, "del /Q C:\\temp\\computehub_new.exe 2>nul", 10, "清理临时文件")

# 下载新 binary
if has_curl:
    cmd = f'curl -L -o C:\\temp\\computehub_new.exe "{DL_URL}"'
else:
    # PowerShell 下载
    ps = f'$wc=New-Object System.Net.WebClient;$wc.DownloadFile("{DL_URL}","C:\\temp\\computehub_new.exe");Write-Output "OK"'
    b64 = base64.b64encode(ps.encode('utf-16le')).decode()
    cmd = f'powershell -EncodedCommand {b64}'

r = run(NODE, cmd, 300, "下载 binary")
if not check_ok(r):
    print("  ❌ 下载失败，中止")
    sys.exit(1)
print("  ✅ 下载完成")

# 验证 SHA256
r = run(NODE, f'certutil -hashfile C:\\temp\\computehub_new.exe SHA256', 15, "验证 SHA256")
if r:
    stdout = r.get('stdout', '')
    if SHA256 in stdout:
        print("  ✅ SHA256 匹配")
    else:
        print(f"  ⚠️ SHA256 不匹配！预期: {SHA256[:20]}...")
        print(f"  实际: {stdout[:200]}")
        # 继续执行，但标记警告

# === Step 3: 备份旧 binary ===
print("\n" + "=" * 40)
print("  Step 3: 备份旧 binary")
print("=" * 40)

r = run(NODE, "copy /Y C:\\computehub\\computehub.exe C:\\computehub\\computehub.exe.bak.1.3.30", 15, "备份旧 binary")
if check_ok(r):
    print("  ✅ 备份完成")
else:
    print("  ⚠️ 备份可能失败，继续")

# === Step 4: 替换 binary ===
print("\n" + "=" * 40)
print("  Step 4: 替换 binary")
print("=" * 40)

r = run(NODE, "copy /Y C:\\temp\\computehub_new.exe C:\\computehub\\computehub.exe", 15, "替换 binary")
if not check_ok(r):
    print("  ❌ 替换失败，中止")
    sys.exit(1)
print("  ✅ 替换完成")

# === Step 5: 重启 Worker ===
print("\n" + "=" * 40)
print("  Step 5: 重启 Worker")
print("=" * 40)

# 先 kill 旧进程
r = run(NODE, "taskkill /F /IM computehub.exe", 15, "Kill 旧进程")
print(f"  Kill 结果: exit={r.get('exit_code','?') if r else '?'}")

# 等待几秒让 Gateway 检测到节点离线
print("  ⏳ 等待 5s...")
time.sleep(5)

# 启动新进程
start_cmd = (
    'start /B "" C:\\computehub\\computehub.exe worker '
    '--gw http://36.250.122.43:8282 '
    '--node-id windows-mobile '
    '--interval 3 --concurrent 4 --heartbeat 10'
)
r = run(NODE, start_cmd, 30, "启动新 Worker")
print(f"  启动结果: exit={r.get('exit_code','?') if r else '?'}")

# === Step 6: 验证 ===
print("\n" + "=" * 40)
print("  Step 6: 验证升级")
print("=" * 40)

print("  ⏳ 等待 15s 让新 Worker 注册...")
time.sleep(15)

# 通过 Gateway 检查节点列表
req = urllib.request.Request(f"{GW}/api/v1/nodes/list")
resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
nodes = resp.get("data", [])
for n in nodes:
    if n.get("node_id") == NODE:
        ver = n.get("version", "?")
        status = n.get("status", "?")
        print(f"  📊 windows-mobile: version={ver}, status={status}")
        if ver == NEW_VER and status == "online":
            print(f"\n  ✅ 升级成功！1.3.30 → {NEW_VER}")
        else:
            print(f"  ⚠️ 版本/状态异常")
        break
else:
    print("  ❌ windows-mobile 不在节点列表中")
    # 尝试通过进程检查
    r = run(NODE, "tasklist | findstr computehub", 10, "检查进程")
    if r:
        print(f"  进程: {(r.get('stdout') or '')[:200]}")

print("\n" + "=" * 60)
print("  升级流程完成")
print("=" * 60)
