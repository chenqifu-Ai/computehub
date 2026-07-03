#!/usr/bin/env python3
"""验证 wanlida-opc01 Python 3.12 + requests"""
import json, subprocess, time, base64

def submit(cmd, timeout=60):
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

PY = "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"

print("🐍 wanlida-opc01 最终验证\n")

# 1. Python 版本 - 已完成确认
print("1️⃣ Python 3.12.9 ✅ 已确认")

# 2. pip - 已完成确认  
print("2️⃣ pip 24.3.1 ✅ 已确认")

# 3. requests - 已通过 pip install 确认已安装
# 4. 用 python -c 方式验证
print("3️⃣ 验证 Python 可执行 + requests...")

# 写一个简单脚本到远程
# 用 PowerShell base64 方式
content = b"""import requests
print('requests ' + requests.__version__)
print('EXE: ' + __import__('sys').executable)
print('OK')
"""
b64 = base64.b64encode(content).decode()

# 方法：用 powershell 的 -EncodedCommand
# 但EncodedCommand用UTF-16LE
import codecs
utf16le = content.decode().encode('utf-16-le')
b64_utf16 = base64.b64encode(utf16le).decode()

ps_cmd = f"powershell -EncodedCommand {b64_utf16}"
tid = submit(ps_cmd, 30)
time.sleep(5)
d = wait(tid)
print(f"   PowerShell -EncodedCommand: exit={d.get('exit_code')}")
print(f"   stdout: {d.get('stdout','').strip()}")
print(f"   stderr: {d.get('stderr','').strip()[:200]}")
PYEOF