#!/usr/bin/env python3
"""
Fedora disk IO test - 2026-05-14
Same test as Windows: 5x 10MB write + 50MB read
"""

import json
import time
import urllib.request

GW = "http://192.168.1.12:8282"

fedora_cmd = """
echo "=== Fedora Disk IO Test (2026-05-14) ==="

# Write test: 5x 10MB
echo "Write 5x 10MB with fdatasync (50MB total)..."
total_write=0
for i in 1 2 3 4 5; do
    start=$(date +%s%N)
    dd if=/dev/zero of=/tmp/fedora_test_${i}.bin bs=1M count=10 conv=fdatasync 2>/dev/null
    end=$(date +%s%N)
    ms=$(( (end - start) / 1000000 ))
    echo "  Write ${i}/5: ${ms}ms"
    total_write=$((total_write + ms))
done
echo "  Total write: ${total_write}ms"

# Read test: 50MB
echo ""
echo "Read 50MB..."
dd if=/tmp/fedora_test_1.bin of=/dev/null bs=1M 2>&1
echo "Read done"

# Cleanup
rm -f /tmp/fedora_test_*.bin

echo ""
echo "=== Fedora Disk IO Test Complete ==="
"""

print(f"Submitting to {GW}/api/v1/tasks/submit")
print(f"Target: fedora-gpu-01")

payload = {"command": fedora_cmd, "node_id": "fedora-gpu-01"}

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
