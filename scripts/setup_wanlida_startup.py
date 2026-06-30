#!/usr/bin/env python3
"""在 wanlida-opc01 上设置开机启动"""
import json, subprocess, time, base64

def submit_b64(b64_cmd, timeout=30):
    """发送 Base64 编码的 PowerShell 命令"""
    r = subprocess.run(
        ["curl", "-s", "-m", "15", "-X", "POST",
         "http://localhost:8282/api/v1/tasks/submit",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({
             "node_id": "wanlida-opc01",
             "task_type": "exec_shell",
             "command": b64_cmd,
             "timeout": timeout
         })],
        capture_output=True, text=True
    )
    return json.loads(r.stdout).get("data", {}).get("task_id", "")

def wait(tid, max_w=60):
    for _ in range(max_w * 2):
        time.sleep(1)
        r2 = subprocess.run(
            ["curl", "-s", "-m", "10",
             f"http://localhost:8282/api/v1/tasks/detail?task_id={tid}"],
            capture_output=True, text=True
        )
        d = json.loads(r2.stdout).get("data", {})
        if d.get("status") in ("completed", "failed"):
            return d
    return {"status": "timeout"}

def run_ps(desc, ps_cmd):
    # PowerShell -EncodedCommand 需要 UTF-16LE 编码的 Base64
    ps_bytes = ps_cmd.encode('utf-16-le')
    b64 = base64.b64encode(ps_bytes).decode('ascii')
    wrapped = f'powershell -EncodedCommand {b64}'
    print(f"\n{desc}")
    tid = submit_b64(wrapped, 25)
    if not tid:
        print(f"   ❌ 提交失败")
        return
    d = wait(tid, 30)
    out = d.get('stdout', '').strip()
    err = d.get('stderr', '').strip()
    if out:
        print(f"   ✓ {out}")
    if err and 'error' in err.lower():
        print(f"   ✗ {err[:200]}")
    else:
        print(f"   完成 (exit={d.get('exit_code')})")

print("=" * 60)
print("设置 wanlida-opc01 开机启动")
print("=" * 60)

# 1. 创建 bat 文件
bat_content = '''@echo off
C:\\installers\\computehub.exe worker --node-id wanlida-opc01 --gw http://36.250.122.43:8282 -d
'''

run_ps("1️⃣ 创建 bat 文件...", 
    f'$content = @"{bat_content}"; [System.IO.File]::WriteAllText("C:\\installers\\start_worker.bat", $content)')

# 2. 验证 bat 文件
run_ps("2️⃣ 验证 bat 文件...", 
    'Get-Content "C:\\installers\\start_worker.bat"')

# 3. 设置计划任务
run_ps("3️⃣ 设置计划任务...",
    'schtasks /create /tn "ComputehubWorker" /tr "C:\\installers\\start_worker.bat" /sc onlogon /ru SYSTEM /rl HIGHEST /F')

# 4. 验证计划任务
run_ps("4️⃣ 验证计划任务...",
    'schtasks /query /tn "ComputehubWorker"')

print("\n" + "=" * 60)
print("✅ 开机启动已配置！")
print("=" * 60)
