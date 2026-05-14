#!/usr/bin/env python3
"""Test fedora-gpu-01 node connectivity - it's registered on Windows Gateway"""

import json
import time
import urllib.request

GW = "http://192.168.1.12:8282"

# Simple test command
cmd = "uname -a && hostname && cat /etc/os-release | grep PRETTY_NAME"

print(f"Submitting to {GW}/api/v1/tasks/submit")
print(f"Target: fedora-gpu-01")

payload = {"command": cmd, "node_id": "fedora-gpu-01"}

req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print(f"Submit result: success={result.get('success')}")

if result.get("success"):
    task_id = result["data"]["task_id"]
    print(f"Task ID: {task_id}")
    print(f"\nWaiting for task completion...")
    
    for i in range(30):
        time.sleep(2)
        try:
            req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}")
            resp2 = urllib.request.urlopen(req2, timeout=10)
            detail = json.loads(resp2.read())
            status = detail["data"]["status"]
            if status in ("completed", "failed", "error"):
                print(f"\n=== Task {status} ===")
                print(f"Exit code: {detail['data'].get('exit_code', 'N/A')}")
                stdout = detail["data"].get("stdout", "")
                stderr = detail["data"].get("stderr", "")
                print(f"\n--- STDOUT ---\n{stdout}")
                if stderr:
                    print(f"\n--- STDERR ---\n{stderr[:500]}")
                break
            else:
                print(f"  [{i+1}/30] Status: {status}")
        except Exception as e:
            print(f"  Check failed: {e}")
