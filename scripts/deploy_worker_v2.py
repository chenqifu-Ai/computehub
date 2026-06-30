#!/usr/bin/env python3
"""部署 Worker - 修复路径问题"""
import json, subprocess, time, base64, sys

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

# 用 PowerShell 直接写文件（不用 base64）
# 路径: C:\installers\dl.py
# 内容:
content = b'''import urllib.request
import os
url = 'http://36.250.122.43:8282/api/v1/download?file=computehub.exe&platform=windows-amd64'
dest = 'C:\\installers\\computehub.exe'
urllib.request.urlretrieve(url, dest)
size = os.path.getsize(dest)
print(f'DOWNLOAD_OK {size} bytes')
'''

b64 = base64.b64encode(content).decode()

print("📤 上传 dl.py...")
ps_cmd = f'powershell -EncodedCommand {b64}'

# PowerShell -EncodedCommand 需要 UTF-16LE
utf16le = content.decode().encode('utf-16-le')
b64_utf16 = base64.b64encode(utf16le).decode()
ps_cmd = f'powershell -EncodedCommand {b64_utf16}'

tid = submit(ps_cmd, 30)
time.sleep(5)
d = wait(tid)
print(f"   exit={d.get('exit_code')}")
print(f"   stdout: {d.get('stdout','')[:300]}")
print(f"   stderr: {d.get('stderr','')[:300]}")

# 检查文件是否存在
print("\n📋 检查文件...")
tid2 = submit('dir C:\\installers\\dl.py')
time.sleep(5)
d2 = wait(tid2)
print(f"   {d2.get('stdout','').strip()[:200]}")

print("\n" + "="*60)
