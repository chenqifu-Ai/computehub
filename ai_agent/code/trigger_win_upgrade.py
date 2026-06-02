#!/usr/bin/env python3
"""Windows Worker 升级 — 直接触发升级引擎"""
import requests
import json
import time

GW = "http://36.250.122.43:8282"

# 通过任务让 Windows Worker 自己升级自己
# worker_agent.go 里注册了 check_and_upgrade 工具
# 调用 Agent API → Agent 自己决定要不要升级
task = {
    "task_id": "trigger-upgrade",
    "node_id": "windows-mobile",
    "command": (
        'powershell -NoProfile -Command "'
        'try { '
        # 先调 Agent 让它检查版本并执行升级
        '$body = @{task=\\"请检查当前版本，如果版本低于1.3.3，调用check_and_upgrade工具执行升级\\"} | ConvertTo-Json -Compress; '
        '$r = Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/think '
        '-Method Post -Body $body -ContentType application/json; '
        'Write-Host ($r | ConvertTo-Json -Depth 3) '
        '} catch { Write-Host Failed: $_.Exception.Message }'
        '"'
    ),
    "timeout": 180
}

print("📤 提交升级任务...")
r = requests.post(f"{GW}/api/v1/tasks/submit", json=task)
print(f"   响应: {r.json()}")

# 轮询结果
for i in range(40):
    time.sleep(5)
    try:
        r2 = requests.post(f"{GW}/api/v1/tasks/progress",
            json={"task_id": task["task_id"], "node_id": "windows-mobile"}, timeout=5)
        d = r2.json()
        if d.get("success"):
            print(f"   [{i*5}s] 任务处理中...")
    except:
        pass

# 检查最终版本
print("\n📊 最终节点状态:")
r3 = requests.get(f"{GW}/api/v1/nodes/list", timeout=5)
for n in r3.json().get("data", []):
    if n.get("node_id") == "windows-mobile":
        for k, v in n.items():
            print(f"   {k}: {v}")
        break