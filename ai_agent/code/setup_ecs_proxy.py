#!/usr/bin/env python3
"""Install socat on ECS and set up WebSocket proxy for OpenClaw"""
import urllib.request, json, time, sys

GW = "http://36.250.122.43:8282"

def submit(node_id, cmd, timeout=30):
    data = json.dumps({"node_id": node_id, "command": cmd, "timeout": timeout, "submitted_by": "agent:duanzhi"}).encode()
    r = urllib.request.urlopen(f"{GW}/api/v1/tasks/submit", data, timeout=timeout+5)
    return json.loads(r.read().decode())

def wait_result(task_id, max_wait=30):
    for _ in range(max_wait//3):
        time.sleep(3)
        r = urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={task_id}", timeout=10)
        d = json.loads(r.read().decode())
        t = d.get("data", {})
        if t.get("status") == "completed":
            return t
    return None

# Step 1: Install socat on ECS
print("=== Step 1: Install socat on ECS ===")
r = submit("ecs-p2ph", "sudo apt-get update -qq && sudo apt-get install -y -qq socat 2>&1 | tail -5", 60)
tid = r.get("data", {}).get("task_id", "")
print(f"Task: {tid}")
t = wait_result(tid, 60)
if t:
    print(f"Exit: {t.get('exit_code')}")
    print(f"Stdout: {t.get('stdout', '')[:500]}")
else:
    print("TIMEOUT")
    sys.exit(1)

# Step 2: Verify socat installed
print("\n=== Step 2: Verify socat ===")
r = submit("ecs-p2ph", "which socat && socat -V 2>&1 | head -2", 10)
tid = r.get("data", {}).get("task_id", "")
t = wait_result(tid)
if t:
    print(f"Exit: {t.get('exit_code')}")
    print(f"Stdout: {t.get('stdout', '')[:300]}")

# Step 3: Start socat proxy (port 18790 -> 127.0.0.1:18789)
print("\n=== Step 3: Start socat proxy ===")
r = submit("ecs-p2ph", "sudo nohup socat TCP-LISTEN:18790,fork,reuseaddr TCP:127.0.0.1:18789 &>/dev/null & echo 'socat started PID:'$!", 10)
tid = r.get("data", {}).get("task_id", "")
t = wait_result(tid)
if t:
    print(f"Exit: {t.get('exit_code')}")
    print(f"Stdout: {t.get('stdout', '')[:300]}")

# Step 4: Verify proxy is listening
print("\n=== Step 4: Verify proxy ===")
r = submit("ecs-p2ph", "ss -tlnp | grep 18790", 10)
tid = r.get("data", {}).get("task_id", "")
t = wait_result(tid)
if t:
    print(f"Exit: {t.get('exit_code')}")
    print(f"Stdout: {t.get('stdout', '')[:300]}")

# Step 5: Test proxy
print("\n=== Step 5: Test proxy ===")
r = submit("ecs-p2ph", "curl -s http://127.0.0.1:18790/health", 10)
tid = r.get("data", {}).get("task_id", "")
t = wait_result(tid)
if t:
    print(f"Exit: {t.get('exit_code')}")
    print(f"Stdout: {t.get('stdout', '')[:300]}")

print("\n=== DONE ===")
print("Now you need to open port 18790 in ECS security group.")
print("Then configure Windows: openclaw config set gateway.remote.url ws://36.250.122.43:18790")
