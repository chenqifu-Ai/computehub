#!/usr/bin/env python3
"""Send command to a worker node via gateway task API"""
import json, urllib.request, sys, time

GW = "http://36.250.122.43:8282"

def submit_task(node_id, command, timeout=30):
    task = {"node_id": node_id, "command": command, "timeout": timeout, "priority": 10}
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps(task).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        return result

def get_task_detail(task_id):
    try:
        with urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={task_id}", timeout=10) as resp:
            return json.loads(resp.read())
    except:
        return None

node = sys.argv[1] if len(sys.argv) > 1 else "windows-home-01"
cmd = sys.argv[2] if len(sys.argv) > 2 else "ver"

print(f"🚀 Submitting task to {node}: {cmd[:80]}...")
result = submit_task(node, cmd, timeout=60)

if result.get("success"):
    task_id = result["data"]["task_id"]
    print(f"✅ Task submitted: {task_id}")
    
    # Wait and poll
    for i in range(10):
        time.sleep(3)
        detail = get_task_detail(task_id)
        if detail and detail.get("success") and detail.get("data"):
            d = detail["data"]
            status = d.get("status", "?")
            print(f"  [{i+1}] Status: {status}")
            if status in ("completed", "failed"):
                print(f"\n{'='*60}")
                print(f"Exit: {d.get('exit_code', '?')}")
                print(f"Stdout: {d.get('stdout', '')[:500]}")
                print(f"Stderr: {d.get('stderr', '')[:500]}")
                print(f"{'='*60}")
                break
    else:
        print("⚠️  Timeout waiting for result")
else:
    print(f"❌ Failed: {result}")