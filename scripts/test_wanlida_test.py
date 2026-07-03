#!/usr/bin/env python3
"""用 --gw 参数正确启动 Worker"""
import json, subprocess, time

def submit(cmd, timeout=60):
    r = subprocess.run(
        ["curl", "-s", "-m", "15", "-X", "POST",
         "http://localhost:8282/api/v1/tasks/submit",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({
             "node_id": "wanlida-test",
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
print("用 --gw 启动 wanlida-test")
print("=" * 60)

cmd = r'C:\installers\computehub.exe worker --node-id wanlida-test --gw http://36.250.122.43:8282 -v'
print(f"命令: {cmd}")

tid = submit(cmd, 35)
time.sleep(15)
d = wait(tid, 35)
print(f"\nexit={d.get('exit_code')}")
import re
for line in d.get('stdout','').split('\n'):
    s = line.strip()
    if s:
        clean = re.sub(r'\x1b\[[0-9;]*m', '', s)
        print(f"  → {clean}")
if d.get('stderr',''):
    for line in d['stderr'].split('\n'):
        if line.strip() and 'poll 失败' not in line and 'connectex' not in line:
            s = line.strip()
            clean = re.sub(r'\x1b\[[0-9;]*m', '', s)
            if 'register' not in clean.lower():
                print(f"  ⚠️ {clean[:200]}")

print("\n" + "=" * 60)
