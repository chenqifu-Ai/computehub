#!/usr/bin/env python3
"""Check ECS for socat/nginx availability"""
import urllib.request, json, time

def submit_task(node_id, command, timeout=10):
    data = json.dumps({"node_id": node_id, "command": command, "timeout": timeout, "submitted_by": "agent:duanzhi"}).encode()
    r = urllib.request.urlopen("http://36.250.122.43:8282/api/v1/tasks/submit", data, timeout=10)
    return json.loads(r.read().decode())

def get_result(task_id):
    r = urllib.request.urlopen(f"http://36.250.122.43:8282/api/v1/tasks/detail?task_id={task_id}", timeout=10)
    return json.loads(r.read().decode())

# Check ECS for socat/nginx
result = submit_task("ecs-p2ph", "which socat; which nginx; ls /usr/bin/socat 2>/dev/null; ls /usr/sbin/nginx 2>/dev/null; apt list --installed 2>/dev/null | grep -E 'socat|nginx'")
task_id = result.get("data", {}).get("task_id", "")
print(f"Task submitted: {task_id}")

time.sleep(5)
for _ in range(5):
    r = get_result(task_id)
    t = r.get("data", {})
    status = t.get("status")
    if status == "completed":
        print(f"Exit: {t.get('exit_code')}")
        print(f"Stdout: {t.get('stdout', '')}")
        print(f"Stderr: {t.get('stderr', '')}")
        break
    print(f"Status: {status}, waiting...")
    time.sleep(3)
