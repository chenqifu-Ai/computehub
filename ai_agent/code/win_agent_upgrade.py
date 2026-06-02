#!/usr/bin/env python3
"""让 Windows Worker 的 Agent 自己执行升级"""
import requests
import json
import time

GW = "http://36.250.122.43:8282"

# Step 1: 发任务 → 让 Worker 调自己的 Agent API (8383)
task = {
    "task_id": "agent-upgrade-win",
    "node_id": "windows-mobile",
    "command": (
        'powershell -Command "'
        'try { '
        '$body = \'{\\"task\\":\\"请检查当前版本，如果低于v1.3.3则执行升级\\"}\'; '
        '$r = Invoke-WebRequest -Uri http://127.0.0.1:8383/api/v1/worker/think '
        '-Method Post -Body $body -ContentType application/json -UseBasicParsing; '
        'Write-Host $r.Content '
        '} catch { Write-Host $_.Exception.Message }'
        '"'
    ),
    "timeout": 120
}

print("🔍 提交 Agent 升级任务...")
r = requests.post(f"{GW}/api/v1/tasks/submit", json=task)
print(f"  提交响应: {r.json()}")
task_id = task["task_id"]

# Step 2: 轮询结果
print(f"⏳ 等待任务完成...")
for i in range(30):
    time.sleep(3)
    try:
        r2 = requests.post(f"{GW}/api/v1/tasks/result", json={"task_id": task_id, "node_id": "windows-mobile"}, timeout=5)
        result = r2.json()
        if result.get("success"):
            data = result.get("data", {})
            print(f"\n✅ 任务完成!")
            print(f"   结果: {json.dumps(data, indent=2, ensure_ascii=False)[:2000]}")
            break
        elif "not found" in str(result):
            # 任务还在执行中
            continue
        else:
            print(f"   中间状态: {result}")
    except Exception as e:
        print(f"   查询异常: {e}")
else:
    print("\n⚠️ 超时，检查节点状态...")

# Step 3: 查看 Worker 状态
r3 = requests.get(f"{GW}/api/v1/nodes/list")
for n in r3.json().get("data", []):
    if n.get("node_id") == "windows-mobile":
        print(f"\n📊 Windows Worker 状态: {json.dumps(n, indent=2, ensure_ascii=False)}")
        break