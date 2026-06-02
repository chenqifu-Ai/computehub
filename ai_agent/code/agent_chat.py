#!/usr/bin/env python3
"""调通 Windows Worker 的 Agent，让它自己决定升级"""
import requests
import json
import time
import sys

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile"

def submit_task(task_id, command, timeout=60):
    r = requests.post(f"{GW}/api/v1/tasks/submit", json={
        "task_id": task_id,
        "node_id": NODE,
        "command": command,
        "timeout": timeout
    })
    data = r.json()
    print(f"  提交: {data.get('success')}")
    return data.get("success", False)

# Step 1: 检查 Worker 的 Agent 状态
print("📡 1. 检查 Worker Agent 状态...")
submit_task("agent-ping", 
    'powershell -NoProfile -Command "try { $r=Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/status -UseBasicParsing; Write-Host ($r|ConvertTo-Json -Compress) } catch { Write-Host ERROR: +$_.Exception.Message }"')

# Step 2: 等结果
print("⏳ 等待结果...")
time.sleep(15)

# Step 3: 看日志
import subprocess
result = subprocess.run([
    "ssh", "-o", "StrictHostKeyChecking=no", "-p", "8022",
    "-i", "/root/.ssh/id_ed25519_computehub",
    "computehub@36.250.122.43",
    "grep -E 'agent-ping|Task.*complete' /home/computehub/gateway.log | tail -5"
], capture_output=True, text=True)
print(f"📋 日志:\n{result.stdout}")

# Step 4: 如果 Agent 通了，让它自己决策升级
print("\n🎯 2. 让 Agent 检查并升级...")
submit_task("agent-upgrade-v133",
    'powershell -NoProfile -Command "try { $body=\'{"""task""":"""请检查当前版本并调用升级工具升级到最新版本"""}\'; $r=Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/think -Method Post -Body $body -ContentType application/json; Write-Host ($r|ConvertTo-Json -Depth 5 -Compress) } catch { Write-Host ERROR: +$_.Exception.Message }"',
    timeout=120)

print("\n⏳ 等待升级完成...")
for i in range(30):
    time.sleep(6)
    # 每轮检查节点是否还活着
    r = requests.get(f"{GW}/api/v1/nodes/list", timeout=5)
    for n in r.json().get("data", []):
        if n.get("node_id") == NODE:
            status = n.get("status")
            tasks = n.get("active_tasks", 0)
            print(f"   [{i*6+6}s] {status}, tasks={tasks}")
            if tasks == 0 and status == "online":
                break
    else:
        continue
    break

# 最终状态
print("\n📊 最终状态:")
r = requests.get(f"{GW}/api/v1/nodes/list", timeout=5)
for n in r.json().get("data", []):
    if n.get("node_id") == NODE:
        print(json.dumps(n, indent=2, ensure_ascii=False))