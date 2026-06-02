#!/usr/bin/env python3
"""Deploy computehub-worker to Windows-mobile via Gateway - base64 encoded PowerShell"""
import json, urllib.request, base64

gw = "http://36.250.122.43:8282"

# Clean PowerShell script - no nested quoting issues
ps_script = """
$url = "http://36.250.122.43:8282/api/v1/download?file=computehub-worker-win-amd64.exe"
$out = "C:\\Users\\xiaomi\\computehub-worker.exe"
Write-Host "[1/3] Downloading new computehub-worker..."
Invoke-WebRequest -Uri $url -OutFile $out
$size = (Get-Item $out).Length / 1MB
Write-Host ("[2/3] Downloaded: {0:F1} MB" -f $size)
Write-Host "[3/3] Starting worker with --agent..."
Get-Process -Name "computehub-worker" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process -FilePath $out -WindowStyle Hidden -ArgumentList "--gw http://36.250.122.43:8282 --node-id Windows-mobile --agent"
Write-Host "DONE: Worker started with --agent"
"""

# Encode to UTF16LE base64 (PowerShell -EncodedCommand format)
ps_bytes = ps_script.encode("utf-16le")
encoded = base64.b64encode(ps_bytes).decode()

task = {
    "node_id": "Windows-mobile",
    "command": f"powershell.exe -EncodedCommand {encoded}"
}

req = urllib.request.Request(
    f"{gw}/api/v1/tasks/submit",
    data=json.dumps(task).encode(),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req, timeout=30) as r:
    resp = json.loads(r.read().decode())
    print("Submit:", json.dumps(resp, indent=2))
    task_id = resp.get("data", {}).get("task_id")

if task_id:
    import time
    for i in range(10):
        time.sleep(3)
        req2 = urllib.request.Request(
            f"{gw}/api/v1/tasks/detail?task_id={task_id}"
        )
        try:
            with urllib.request.urlopen(req2, timeout=10) as r2:
                detail = json.loads(r2.read().decode())
                data = detail.get("data", {})
                status = data.get("status", "unknown")
                print(f"[{i+1}] status={status}")
                if status == "completed":
                    stdout = data.get("stdout", "")
                    stderr = data.get("stderr", "")
                    exit_code = data.get("exit_code")
                    print(f"  exit_code={exit_code}")
                    if stdout: print(f"  stdout: {stdout.strip()}")
                    if stderr: print(f"  stderr: {stderr.strip()}")
                    break
        except Exception as e:
            print(f"  error: {e}")
    
    # Final node list
    time.sleep(3)
    req3 = urllib.request.Request(f"{gw}/api/v1/nodes/list")
    with urllib.request.urlopen(req3, timeout=10) as r3:
        nodes = json.loads(r3.read().decode())
        print("\n=== Nodes ===")
        for n in nodes.get("data", []):
            print(f"  {n['node_id']}: {n['status']}")