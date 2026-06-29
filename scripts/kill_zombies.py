#!/usr/bin/env python3
import json, subprocess, sys

def cancel_task(task_id):
    cmd = f'curl -s -X POST http://127.0.0.1:8282/api/v1/tasks/cancel -H "Content-Type: application/json" -d \'{json.dumps({"task_id": task_id, "reason": "zombie"})}\''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    try:
        resp = json.loads(result.stdout)
        return resp.get("success", False)
    except:
        return False

data = subprocess.run("curl -s http://127.0.0.1:8282/api/v1/tasks/list", shell=True, capture_output=True, text=True, timeout=15)
tasks_data = json.loads(data.stdout)

zombies = []
for node_id, task_list in tasks_data.get("data", {}).items():
    for t in task_list:
        if t.get("status") == "running":
            zombies.append(t["task_id"])

print(f"发现 {len(zombies)} 个 running 任务")

success = 0
for tid in zombies:
    if cancel_task(tid):
        success += 1
        print(f"  ✅ {tid}")

print(f"取消成功：{success}/{len(zombies)}")
