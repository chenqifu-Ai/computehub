#!/usr/bin/env python3
import json, urllib.request

GW = "http://36.250.122.43:8282"

# Step 1: Find deploy dir on ecs-p2ph
task = json.dumps({"node_id": "ecs-p2ph", "task_type": "exec", "payload": "ls -la ~/deploy/", "timeout": 8})
req = urllib.request.Request(f"{GW}/api/v1/tasks/submit", data=task.encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as r:
    t1 = json.loads(r.read())
tid1 = t1["data"]["task_id"]
print(f"Task 1: {tid1}")

import time
for _ in range(8):
    req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={tid1}&node_id=ecs-p2ph")
    with urllib.request.urlopen(req2) as r:
        d = json.loads(r.read())
    if d["data"]["status"] == "completed":
        print("stdout:", d["data"].get("stdout",""))
        print("stderr:", d["data"].get("stderr",""))
        break
    time.sleep(1)

# Step 2: Upload binary to ECS via scp task
import base64
with open("/tmp/computehub-linux-amd64", "rb") as f:
    b64data = base64.b64encode(f.read()).decode()

# Use a task to write the binary (via base64 decode)
write_cmd = f"echo '{b64data}' | base64 -d > /tmp/computehub-new && chmod +x /tmp/computehub-new && ls -la /tmp/computehub-new"

task2 = json.dumps({"node_id": "ecs-p2ph", "task_type": "exec", "payload": write_cmd, "timeout": 30})
req3 = urllib.request.Request(f"{GW}/api/v1/tasks/submit", data=task2.encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req3) as r:
    t2 = json.loads(r.read())
tid2 = t2["data"]["task_id"]
print(f"Task 2 (upload): {tid2}")

for _ in range(15):
    req4 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={tid2}&node_id=ecs-p2ph")
    with urllib.request.urlopen(req4) as r:
        d = json.loads(r.read())
    if d["data"]["status"] == "completed":
        print("Upload stdout:", d["data"].get("stdout",""))
        print("Upload stderr:", d["data"].get("stderr",""))
        break
    time.sleep(2)
else:
    print("Upload timed out")