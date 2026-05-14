#!/usr/bin/env python3
"""Submit disk IO test to Fedora node for comparison"""

import json
import time
import urllib.request

GW = "http://192.168.1.12:8282"

# Same 50MB sequential read/write test for Fedora (uses dd + hdparm style)
fedora_cmd = """
# Create test file
dd if=/dev/urandom of=/tmp/testdisk_50mb.bin bs=1M count=50 2>/dev/null
# Sequential write speed
echo "=== Disk Write Test (50MB) ==="
time (dd if=/dev/zero of=/tmp/testdisk_write.bin bs=1M count=50 conv=fdatasync oflag=direct 2>&1) || \
time (dd if=/dev/zero of=/tmp/testdisk_write.bin bs=1M count=50 conv=fdatasync 2>&1)
# Sequential read speed
echo ""
echo "=== Disk Read Test ==="
time (dd if=/tmp/testdisk_50mb.bin of=/dev/null bs=1M 2>&1)
# Cleanup
rm -f /tmp/testdisk_50mb.bin /tmp/testdisk_write.bin
echo ""
echo "=== Disk IO Test Complete ==="
""".strip()

payload = {
    "command": fedora_cmd,
    "node_id": "fedora-gpu-01",
}

print(f"Submitting to {GW}/api/v1/tasks/submit")
print(f"Target: fedora-gpu-01")

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
    
    for i in range(60):
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
                print(f"  [{i+1}/60] Status: {status}")
        except Exception as e:
            print(f"  Check failed: {e}")
