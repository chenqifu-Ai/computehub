#!/usr/bin/env python3
"""Submit disk IO test to Windows node - using base64-encoded PowerShell"""

import json
import base64
import time
import urllib.request

GW = "http://192.168.1.12:8282"

# Build a simple PowerShell script (no quotes issues since we'll base64 encode it)
ps_script = r'''
$testDir = "D:\testdisk"
$testFile = Join-Path $testDir "testfile.bin"
if (-not (Test-Path $testDir)) { New-Item -ItemType Directory -Path $testDir -Force | Out-Null }

Write-Host "=== Disk Write Test (50MB) ==="
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$data = [byte[]]::new(10485760)
[System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($data)
$stream = [System.IO.File]::OpenWrite($testFile)
for ($i = 0; $i -lt 5; $i++) { $stream.Write($data, 0, $data.Length) }
$stream.Close()
$stopwatch.Stop()
Write-Host "50MB sequential write: $($stopwatch.ElapsedMilliseconds)ms"

Write-Host ""
Write-Host "=== Disk Read Test ==="
$stopwatch.Reset()
$stopwatch.Start()
$rstream = [System.IO.File]::OpenRead($testFile)
$buffer = [byte[]]::new(10485760)
$totalRead = 0
while ($true) {
    $bytesRead = $rstream.Read($buffer, 0, $buffer.Length)
    if ($bytesRead -eq 0) break
    $totalRead += $bytesRead
}
$rstream.Close()
$stopwatch.Stop()
$readMB = $totalRead / (1024*1024)
Write-Host "$([math]::Round($readMB,2))MB sequential read: $($stopwatch.ElapsedMilliseconds)ms"

Remove-Item $testFile -Force
Write-Host ""
Write-Host "=== Disk IO Test Complete ==="
'''

# Base64 encode (UTF-16LE for PowerShell -EncodedCommand)
script_bytes = ps_script.encode('utf-16-le')
b64_cmd = base64.b64encode(script_bytes).decode('ascii')

command = f"powershell -EncodedCommand {b64_cmd}"

print(f"Submitting to {GW}/api/v1/tasks/submit")
print(f"Target: worker-DESKTOP-BUAUIFL")
print(f"Encoded command length: {len(b64_cmd)} chars")

payload = {
    "command": command,
    "node_id": "worker-DESKTOP-BUAUIFL"
}

req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print(f"\nSubmit result: {json.dumps(result, indent=2)}")

task_id = result.get("data", {}).get("task_id", "")
if not task_id:
    print("ERROR: No task_id in response")
    exit(1)

print(f"\nWaiting for task (task_id={task_id})...")
for i in range(60):
    time.sleep(2)
    try:
        req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        detail = json.loads(resp2.read())
        status = detail.get("data", {}).get("status", "")
        if status in ("completed", "failed", "error"):
            print(f"\nTask status: {status}")
            print(f"Exit code: {detail.get('data', {}).get('exit_code', 'N/A')}")
            stdout = detail.get('data', {}).get('stdout', '')
            stderr = detail.get('data', {}).get('stderr', '')
            print(f"\n=== STDOUT ===\n{stdout}")
            if stderr:
                print(f"\n=== STDERR (truncated) ===\n{stderr[:500]}")
            break
        else:
            print(f"  [{i+1}/60] Status: {status}")
    except Exception as e:
        print(f"  Check failed: {e}")
