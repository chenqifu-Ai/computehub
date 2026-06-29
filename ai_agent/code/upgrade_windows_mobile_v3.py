#!/usr/bin/env python3
"""
升级 windows-mobile: 1.3.30 → 1.3.42
v3 — 全 PowerShell 兼容语法（Gateway 自动包装 PowerShell）
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

def run_ps(node_id, ps_code, timeout=60, label=""):
    """提交 PowerShell 脚本（UTF-16LE base64 编码）"""
    label = label or "PS脚本"
    b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
    cmd = f'powershell -EncodedCommand {b64}'
    print(f"\n  ▶ {label}")
    task_id = submit(node_id, cmd, timeout)
    result = wait(task_id, max_wait=timeout+30)
    if result:
        ec = result.get('exit_code', '?')
        stdout = (result.get('stdout') or '')[:500]
        stderr = (result.get('stderr') or '')[:200]
        print(f"  Exit: {ec}")
        if stdout: print(f"  Out: {stdout}")
        if stderr: print(f"  Err: {stderr}")
        return result
    else:
        print(f"  ⚠️ 超时/无结果")
        return None

def run_raw(node_id, cmd, timeout=60, label=""):
    label = label or cmd[:50]
    print(f"\n  ▶ {label}")
    task_id = submit(node_id, cmd, timeout)
    result = wait(task_id, max_wait=timeout+30)
    if result:
        ec = result.get('exit_code', '?')
        stdout = (result.get('stdout') or '')[:500]
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

r = run_raw(NODE, "echo OK", 10, "echo OK")
if not check_ok(r):
    print("  ❌ 节点不可达，中止")
    sys.exit(1)
print("  ✅ 节点在线")

# === Step 1: 查进程路径 ===
print("\n" + "=" * 40)
print("  Step 1: 查进程信息")
print("=" * 40)

ps_check = r"""
$p = Get-CimInstance Win32_Process -Filter "name='computehub.exe'" | Select-Object ExecutablePath,CommandLine
if ($p) { $p.ExecutablePath } else { "NOT_FOUND" }
"""
r = run_ps(NODE, ps_check, 30, "查进程路径")
binary_path = None
if r:
    stdout = r.get('stdout', '')
    print(f"  路径: {stdout[:200]}")
    if stdout and 'NOT_FOUND' not in stdout:
        # 提取路径
        for line in stdout.split('\n'):
            line = line.strip()
            if line and '\\' in line and line.endswith('.exe'):
                binary_path = line
                break

if not binary_path:
    # 尝试常见路径
    ps_find = r"""
$paths = @(
    'C:\computehub\computehub.exe',
    'C:\Users\admin\computehub\computehub.exe',
    'C:\Users\xiaomi\computehub\computehub.exe',
    'C:\Program Files\computehub\computehub.exe'
)
foreach ($p in $paths) {
    if (Test-Path $p) { Write-Output "EXISTS:$p" }
}
"""
    r = run_ps(NODE, ps_find, 30, "查找 binary")
    if r:
        stdout = r.get('stdout', '')
        print(f"  查找结果:\n{stdout}")
        for line in stdout.split('\n'):
            if line.startswith('EXISTS:'):
                binary_path = line.replace('EXISTS:', '').strip()
                print(f"  ✅ 找到: {binary_path}")
                break

if not binary_path:
    binary_path = "C:\\computehub\\computehub.exe"
    print(f"  ⚠️ 使用默认路径: {binary_path}")

# === Step 2: 下载新 binary ===
print("\n" + "=" * 40)
print(f"  Step 2: 下载 v{NEW_VER} binary")
print("=" * 40)

ps_dl = f"""
$wc = New-Object System.Net.WebClient
try {{
    $wc.DownloadFile('{DL_URL}', 'C:\\temp\\computehub_new.exe')
    Write-Output 'OK'
}} catch {{
    Write-Output "ERROR:$($_.Exception.Message)"
}}
"""
r = run_ps(NODE, ps_dl, 300, "下载 binary")
if not check_ok(r):
    print("  ❌ 下载失败，中止")
    sys.exit(1)
print("  ✅ 下载完成")

# 验证 SHA256
ps_sha = r"""
$hash = (Get-FileHash -Path 'C:\temp\computehub_new.exe' -Algorithm SHA256).Hash
Write-Output $hash
"""
r = run_ps(NODE, ps_sha, 30, "验证 SHA256")
if r:
    stdout = r.get('stdout', '').strip()
    if SHA256 in stdout:
        print("  ✅ SHA256 匹配")
    else:
        print(f"  ⚠️ SHA256 不匹配！")
        print(f"  预期: {SHA256}")
        print(f"  实际: {stdout[:100]}")

# === Step 3: 备份旧 binary ===
print("\n" + "=" * 40)
print("  Step 3: 备份旧 binary")
print("=" * 40)

ps_bak = f"""
Copy-Item -Path '{binary_path}' -Destination '{binary_path}.bak.1.3.30' -Force
Write-Output 'OK'
"""
r = run_ps(NODE, ps_bak, 30, "备份旧 binary")
if r:
    print(f"  备份: {(r.get('stdout') or '')[:200]}")

# === Step 4: 替换 binary ===
print("\n" + "=" * 40)
print("  Step 4: 替换 binary")
print("=" * 40)

ps_cp = f"""
Copy-Item -Path 'C:\\temp\\computehub_new.exe' -Destination '{binary_path}' -Force
Write-Output 'OK'
"""
r = run_ps(NODE, ps_cp, 30, "替换 binary")
if not check_ok(r):
    print("  ❌ 替换失败，中止")
    sys.exit(1)
print("  ✅ 替换完成")

# === Step 5: 重启 Worker ===
print("\n" + "=" * 40)
print("  Step 5: 重启 Worker")
print("=" * 40)

# Kill 旧进程
r = run_raw(NODE, "taskkill /F /IM computehub.exe", 15, "Kill 旧进程")
print(f"  Kill: exit={r.get('exit_code','?') if r else '?'}")

print("  ⏳ 等待 10s...")
time.sleep(10)

# 启动新进程
start_cmd = (
    'start /B "" C:\\computehub\\computehub.exe worker '
    '--gw http://36.250.122.43:8282 '
    '--node-id windows-mobile '
    '--interval 3 --concurrent 4 --heartbeat 10'
)
r = run_raw(NODE, start_cmd, 30, "启动新 Worker")
print(f"  启动: exit={r.get('exit_code','?') if r else '?'}")

# === Step 6: 验证 ===
print("\n" + "=" * 40)
print("  Step 6: 验证升级")
print("=" * 40)

print("  ⏳ 等待 20s 让新 Worker 注册...")
time.sleep(20)

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
            print(f"  ⚠️ 版本/状态异常: version={ver}, status={status}")
        break
else:
    print("  ❌ windows-mobile 不在节点列表中")

print("\n" + "=" * 60)
print("  升级流程完成")
print("=" * 60)
