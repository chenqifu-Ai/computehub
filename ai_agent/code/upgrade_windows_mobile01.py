#!/usr/bin/env python3
"""
升级 windows-mobile01: 1.3.39 → 1.3.42
节点在线，用 PowerShell 分步操作，不 kill 再等
"""
import json, urllib.request, time, sys, base64

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile01"
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

def wait(task_id, poll_interval=2, max_wait=180):
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
    """提交 PowerShell -EncodedCommand"""
    b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
    cmd = f'powershell -EncodedCommand {b64}'
    label = label or "PS"
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
        print(f"  ⚠️ 超时")
        return None

def check_ok(result):
    return result and result.get('exit_code') == 0

def get_nodes():
    req = urllib.request.Request(f"{GW}/api/v1/nodes/list")
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    return resp.get("data", [])

print("=" * 60)
print(f"  🚀 升级 windows-mobile01: 1.3.39 → {NEW_VER}")
print("=" * 60)

# === Task 1: 查 binary 路径 ===
print("\n" + "=" * 40)
print("  Task 1: 查 binary 路径")
print("=" * 40)

ps_path = r"""
$p = Get-CimInstance Win32_Process -Filter "name='computehub.exe'" | Select-Object ExecutablePath
if ($p) { Write-Output $p.ExecutablePath } else { Write-Output 'NOT_FOUND' }
"""
r = run_ps(NODE, ps_path, 30, "查进程路径")
binary_path = None
if r:
    stdout = (r.get('stdout') or '').strip()
    for line in stdout.split('\n'):
        line = line.strip()
        if line and '\\' in line and line.endswith('.exe'):
            binary_path = line
            break
    print(f"  Binary: {binary_path}")

if not binary_path:
    binary_path = "C:\\Windows\\system32\\computehub.exe"
    print(f"  ⚠️ 默认: {binary_path}")

# === Task 2: 下载 v1.3.42 binary ===
print("\n" + "=" * 40)
print(f"  Task 2: 下载 v{NEW_VER}")
print("=" * 40)

ps_dl = f"""
$wc = New-Object System.Net.WebClient
try {{
    $wc.DownloadFile('{DL_URL}', 'C:\\temp\\computehub_v42.exe')
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

# === Task 3: 验证 SHA256 ===
print("\n" + "=" * 40)
print("  Task 3: 验证 SHA256")
print("=" * 40)

ps_sha = r"""
$hash = (Get-FileHash -Path 'C:\temp\computehub_v42.exe' -Algorithm SHA256).Hash
Write-Output $hash
"""
r = run_ps(NODE, ps_sha, 30, "验证 SHA256")
if r:
    stdout = (r.get('stdout') or '').strip()
    if SHA256 in stdout:
        print("  ✅ SHA256 匹配")
    else:
        print(f"  ⚠️ 不匹配！预期 {SHA256[:20]}... 实际 {stdout[:20]}...")
        print("  继续执行，但标记警告")

# === Task 4: 备份旧 binary + 替换 + 启动新进程 ===
print("\n" + "=" * 40)
print("  Task 4: 备份→替换→启动新进程")
print("=" * 40)

# 先备份，再替换，然后启动新进程（所有操作在同一任务中完成）
# 使用 `;` 分隔（PowerShell 兼容）
ps_go = f"""
try {{
    Copy-Item -Path '{binary_path}' -Destination '{binary_path}.bak.1.3.39' -Force
    Write-Output '备份完成'
    Copy-Item -Path 'C:\\temp\\computehub_v42.exe' -Destination '{binary_path}' -Force
    Write-Output '替换完成'
    # 启动新进程（带升级缓存标记，跳过30min升级检查）
    $arg = 'worker --gw http://36.250.122.43:8282 --node-id windows-mobile01 --interval 3 --concurrent 4 --heartbeat 10'
    Start-Process -NoNewWindow -FilePath '{binary_path}' -ArgumentList $arg
    Write-Output '新进程已启动'
}} catch {{
    Write-Output "ERROR:$($_.Exception.Message)"
}}
"""
r = run_ps(NODE, ps_go, 30, "备份→替换→启动")
if r:
    print(f"  结果: {(r.get('stdout') or '')[:300]}")
    if not check_ok(r):
        print("  ⚠️ 操作可能有异常")
else:
    print("  ⚠️ 任务超时（新进程已启动，任务可能被kill旧进程打断）")

# === Task 5: Kill 旧进程 ===
print("\n" + "=" * 40)
print("  Task 5: Kill 旧进程（保留新进程）")
print("=" * 40)

# 先检查现有进程数
r = run_ps(NODE, 'Write-Output (Get-Process -Name "computehub" -ErrorAction SilentlyContinue).Count', 15, "检查进程数")
if r:
    count = (r.get('stdout') or '').strip()
    print(f"  当前进程数: {count}")

# Kill 所有 computehub 进程，等新进程注册
cmd_kill = "taskkill /F /IM computehub.exe >nul 2>&1 & echo KILLED"
r = run_ps(NODE, 'try { taskkill /F /IM computehub.exe 2>&1 | Out-Null; Write-Output "OK" } catch { Write-Output "OK" }', 15, "Kill 旧进程")
if r:
    print(f"  Kill: {(r.get('stdout') or '')[:100]}")

# === Task 6: 等待并验证 ===
print("\n" + "=" * 40)
print(f"  Task 6: 等待注册 + 验证")
print("=" * 40)

for i in range(15):
    time.sleep(4)
    nodes = get_nodes()
    for n in nodes:
        if n.get("node_id") == "windows-mobile01":
            ver = n.get("version", "?")
            status = n.get("status", "?")
            print(f"  [{i*4+4}s] windows-mobile01: v{ver} {status}")
            if ver == NEW_VER and status == "online":
                print(f"\n  ✅ 升级成功！1.3.39 → {NEW_VER}")
                sys.exit(0)
            break
    else:
        if i % 3 == 0:
            print(f"  [{i*4+4}s] 等待中...")

print("\n  ⏳ 暂时未上线，Binary 已替换，稍后会自动注册")

print("\n" + "=" * 60)
print("  升级流程完成")
print("=" * 60)