#!/usr/bin/env python3
"""跟 Windows Worker Agent 聊天 - 先了解它"""
import requests
import json
import time

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile"

def run_cmd(task_id, cmd, timeout=30):
    r = requests.post(f"{GW}/api/v1/tasks/submit", json={
        "task_id": task_id,
        "node_id": NODE,
        "command": cmd,
        "timeout": timeout
    })
    print(f"→ {task_id}: 已提交")
    return task_id

# 1. 看看 Agent 的健康状态（最轻量）
run_cmd("explore-01-health",
    'powershell -NoProfile -Command "try { Write-Host ===HEALTH===; $r=Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/health -UseBasicParsing; $r | ConvertTo-Json } catch { Write-Host FAIL: $_.Exception.Message }"')

time.sleep(5)

# 2. 看看 Agent 的完整状态（含诊断信息）
run_cmd("explore-02-status",
    'powershell -NoProfile -Command "try { Write-Host ===STATUS===; $r=Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/status -UseBasicParsing; $r | ConvertTo-Json -Depth 5 } catch { Write-Host FAIL: $_.Exception.Message }"')

time.sleep(5)

# 3. 问问 Agent 它会什么、有哪些工具
run_cmd("explore-03-whatcanyoudo",
    'powershell -NoProfile -Command "try { Write-Host ===THINK===; $body=\'{"""task""":"""请列出你所有可用的工具和功能，你擅长做什么？""", """session_id""":"""explore-session"""}\'; $r=Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/think -Method Post -Body $body -ContentType application/json -UseBasicParsing; Write-Host ($r | ConvertTo-Json -Depth 5) } catch { Write-Host FAIL: $_.Exception.Message }"',
    timeout=120)

print("\n📡 等待 Agent 回答...")
time.sleep(120)

# 收集结果
import subprocess
result = subprocess.run([
    "ssh", "-o", "StrictHostKeyChecking=no", "-p", "8022",
    "-i", "/root/.ssh/id_ed25519_computehub",
    "computehub@36.250.122.43",
    "grep -E 'explore-' /home/computehub/gateway.log | grep -v Heartbeat | grep -v heartbeat | grep -v 'Command gw-'"
], capture_output=True, text=True)
print("\n📋 Agent 回答摘要:")
print(result.stdout)