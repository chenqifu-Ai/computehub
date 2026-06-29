#!/usr/bin/env python3
"""Upgrade windows-home-01 node to v1.3.24 via gateway task API"""
import json, urllib.request, sys

GW = "http://36.250.122.43:8282"

# Step 1: Submit download + replace task (Phase 1)
# certutil download, copy over original, then restart worker
cmd = (
    'certutil -urlcache -f http://36.250.122.43:8282/api/v1/download?file=computehub-windows-amd64.exe D:\\computehub\\computehub.v1.3.24.exe >nul 2>&1 && '
    'copy /Y D:\\computehub\\computehub.v1.3.24.exe D:\\computehub\\computehub.exe >nul 2>&1 && '
    'start /B D:\\computehub\\computehub.exe worker --gw http://36.250.122.43:8282 --node-id windows-home-01 --interval 3 --concurrent 2 --heartbeat 10'
)

task = {
    "node_id": "windows-home-01",
    "command": cmd,
    "timeout": 120,
    "max_retries": 2,
    "priority": 10
}

req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(task).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        print(f"✅ Task submitted: {json.dumps(result, indent=2, ensure_ascii=False)}")
        if result.get("success"):
            task_id = result.get("data", {}).get("task_id", "")
            print(f"\n📋 Task ID: {task_id}")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)