#!/usr/bin/env python3
"""Fix Windows command encoding and retest"""
import json, time, base64, urllib.request

GW = "http://192.168.1.12:8282"

# Test: simple PowerShell command that needs base64 encoding
ps_script = """
$a = 0; $b = 1
for ($i = 2; $i -le 35; $i++) { $t = $a + $b; $a = $b; $b = $t }
Write-Host "FIB=$b"
"""

b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
cmd = f"powershell -EncodedCommand {b64}"

print(f"Command length: {len(cmd)}")
print(f"Submitting to worker-DESKTOP-BUAUIFL...")

req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps({"command": cmd, "node_id": "worker-DESKTOP-BUAUIFL"}).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=10)
task_id = json.loads(resp.read())["data"]["task_id"]
print(f"Task ID: {task_id}")

for _ in range(30):
    time.sleep(2)
    try:
        resp = urllib.request.urlopen(
            urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
            timeout=10
        )
        detail = json.loads(resp.read())
        if detail["data"]["status"] in ("completed", "failed"):
            print(f"Status: {detail['data']['status']}")
            print(f"Exit: {detail['data'].get('exit_code')}")
            print(f"Stdout: {detail['data'].get('stdout', '')}")
            print(f"Stderr: {detail['data'].get('stderr', '')}")
            break
    except:
        pass
