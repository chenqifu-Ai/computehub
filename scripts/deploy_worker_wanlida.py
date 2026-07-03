#!/usr/bin/env python3
"""部署 ComputeHub Worker 到 wanlida-opc01"""
import json, subprocess, time

def submit(cmd, timeout=120):
    r = subprocess.run(
        ["curl", "-s", "-m", "15", "-X", "POST",
         "http://localhost:8282/api/v1/tasks/submit",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({
             "node_id": "wanlida-opc01",
             "task_type": "exec_shell",
             "command": cmd,
             "timeout": timeout
         })],
        capture_output=True, text=True
    )
    return json.loads(r.stdout).get("data", {}).get("task_id", "")

def wait(tid, max_w=120):
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

print("=" * 60)
print("🚀 部署 ComputeHub Worker 到 wanlida-opc01")
print("=" * 60)

# 步骤1: 下载 Worker binary
print("\n1️⃣ 下载 Worker binary...")
GATEWAY = "http://localhost:8282"
cmd1 = f'curl -sL -o C:\\\\installers\\\\computehub.exe {GATEWAY}/api/v1/download?file=computehub.exe&platform=windows-amd64 -m 120 && echo DOWNLOAD_OK || echo DOWNLOAD_FAILED'
tid1 = submit(cmd1, 120)
time.sleep(10)
d1 = wait(tid1, 120)
print(f"   exit={d1.get('exit_code')}")
print(f"   stdout: {d1.get('stdout','').strip()[:200]}")

# 检查文件
tid2 = submit('dir C:\\\\installers\\\\computehub.exe 2>&1 | findstr computehub.exe')
time.sleep(5)
d2 = wait(tid2)
print(f"   文件大小: {d2.get('stdout','').strip()[:200]}")

# 步骤2: 验证 binary
print("\n2️⃣ 验证 binary...")
cmd2 = 'C:\\\\installers\\\\computehub.exe --version 2>&1 || echo VERSION_FAIL'
tid3 = submit(cmd2, 30)
time.sleep(5)
d3 = wait(tid3)
print(f"   exit={d3.get('exit_code')}")
print(f"   stdout: {d3.get('stdout','').strip()[:200]}")
if d3.get('stderr',''):
    print(f"   stderr: {d3.get('stderr','').strip()[:200]}")

print("\n" + "=" * 60)
