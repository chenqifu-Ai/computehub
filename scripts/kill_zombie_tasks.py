#!/usr/bin/env python3
"""批量取消所有 running 任务"""
import subprocess, json

SSH = "ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43"

# 获取所有 running 任务
cmd = f'{SSH} "curl -s http://127.0.0.1:8282/api/v1/tasks/list"'
data = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
tasks = json.loads(data.stdout)

zombies = []
for node_id, task_list in tasks.get("data", {}).items():
    for t in task_list:
        if t.get("status") == "running":
            zombies.append(t["task_id"])

print(f"发现 {len(zombies)} 个僵尸任务")

# 批量取消
success = 0
for tid in zombies:
    cmd = f'{SSH} "curl -s -X POST http://127.0.0.1:8282/api/v1/tasks/cancel -H \'Content-Type: application/json\' -d \'{{\\"task_id\\": \\"{tid}\\", \\"reason\\": \\"zombie\\"}}\'"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    try:
        resp = json.loads(result.stdout)
        if resp.get("success"):
            success += 1
            print(f"  ✅ {tid}")
        else:
            print(f"  ❌ {tid}")
    except:
        print(f"  ❌ {tid}")

print(f"\n取消成功：{success}/{len(zombies)}")
