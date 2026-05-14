#!/usr/bin/env python3
"""
Test: 3 nodes execute tasks concurrently with distinct signatures.
Verify each node returns correct result (task routing is accurate).
"""

import json
import time
import base64
import urllib.request

GW = "http://192.168.1.12:8282"

nodes = {
    "fedora-gpu-01": {
        "command": "echo 'TASK_ID=FEDORA'; uname -a; hostname; echo '=== FEDORA IS RUNNING ==='",
        "expected_id": "FEDORA"
    },
    "worker-DESKTOP-BUAUIFL": {
        "command": None,  # will be set below
        "expected_id": "WINDOWS"
    },
    "redmi-1": {
        "command": "echo 'TASK_ID=REDMI'; uname -a; hostname; echo '=== REDMI IS RUNNING ==='",
        "expected_id": "REDMI"
    }
}

# Fix Windows command with proper base64
ps_script = r'Write-Host "TASK_ID=WINDOWS"; hostname; Write-Host "=== WINDOWS IS RUNNING ==="'
b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
nodes["worker-DESKTOP-BUAUIFL"]["command"] = f"powershell -EncodedCommand {b64}"

# Submit all 3 tasks simultaneously
print("=" * 60)
print("SUBMITTING 3 TASKS CONCURRENTLY")
print("=" * 60)

results = {}
task_ids = {}

for node_id, task_info in nodes.items():
    payload = {
        "command": task_info["command"],
        "node_id": node_id
    }
    print(f"\n-> Submitting to {node_id}...")
    
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read())
    
    if result.get("success"):
        task_id = result["data"]["task_id"]
        task_ids[node_id] = task_id
        print(f"   Task ID: {task_id}")
    else:
        print(f"   ERROR: {result.get('error')}")

# Wait for all tasks to complete
print("\n" + "=" * 60)
print("WAITING FOR COMPLETION")
print("=" * 60)

for i in range(60):
    completed = sum(1 for n in task_ids if n in results)
    if completed == len(task_ids):
        break
    print(f"  [{i+1}/60] {completed}/{len(task_ids)} completed")
    time.sleep(2)
    
    for node_id, task_id in task_ids.items():
        if node_id in results:
            continue
        try:
            req = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}")
            resp = urllib.request.urlopen(req, timeout=10)
            detail = json.loads(resp.read())
            status = detail["data"]["status"]
            if status in ("completed", "failed", "error"):
                results[node_id] = {
                    "stdout": detail["data"].get("stdout", ""),
                    "stderr": detail["data"].get("stderr", ""),
                    "exit_code": detail["data"].get("exit_code"),
                    "status": status
                }
        except Exception as e:
            pass

# Print results
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)

all_pass = True
for node_id in nodes:
    task_info = nodes[node_id]
    print(f"\n[{node_id}]")
    
    if node_id not in results:
        print("  ❌ TIMEOUT")
        all_pass = False
        continue
    
    result = results[node_id]
    expected = task_info["expected_id"]
    stdout = result["stdout"].strip()
    passed = expected in stdout
    
    if passed:
        print(f"  ✅ PASS")
    else:
        print(f"  ❌ FAIL (expected '{expected}')")
        all_pass = False
    
    print(f"  Exit: {result.get('exit_code')} | Status: {result.get('status')}")
    print(f"  Output:")
    for line in stdout.split("\n")[:5]:
        print(f"    {line}")

print("\n" + "=" * 60)
if all_pass:
    print("✅ ALL 3 TASKS ROUTED CORRECTLY")
else:
    print("❌ ROUTING FAILED")
print("=" * 60)
