#!/usr/bin/env python3
"""Submit disk IO test to Windows node via ComputeHub API"""

import json
import time
import urllib.request
import urllib.error

GW = "http://localhost:8282"

# Write the PowerShell script to a file and send as command
powershell_script = r'''
$testDir = "D:\testdisk"
$testFile = Join-Path $testDir "testfile.bin"
if (-not (Test-Path $testDir)) { New-Item -ItemType Directory -Path $testDir -Force | Out-Null }

Write-Host "=== Disk Write Test ==="
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$data = New-Object byte[] 10485760
(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($data)
$stream = [System.IO.File]::OpenWrite($testFile)
for ($i = 0; $i -lt 5; $i++) { $stream.Write($data, 0, $data.Length) }
$stream.Close()
$stopwatch.Stop()
$writeMs = $stopwatch.ElapsedMilliseconds
Write-Host "50MB sequential write: ${writeMs}ms"

Write-Host ""
Write-Host "=== Disk Read Test ==="
$stopwatch.Reset()
$stopwatch.Start()
$rstream = [System.IO.File]::OpenRead($testFile)
$buffer = New-Object byte[] 10485760
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

# Cleanup
Remove-Item $testFile -Force
Write-Host ""
Write-Host "=== Done ==="
'''

# Save PowerShell script
with open('/root/.openclaw/workspace/ai_agent/code/win_disk_test.ps1', 'w') as f:
    f.write(powershell_script)

# Submit to Windows node
payload = {
    "command": f"powershell -ExecutionPolicy Bypass -File /root/.openclaw/workspace/ai_agent/code/win_disk_test.ps1",
    "node_id": "worker-DESKTOP-BUAUIFL"
}

print(f"Submitting task to {GW}/api/v1/tasks/submit ...")
req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print(f"Submit result: {json.dumps(result, indent=2)}")

task_id = result.get("data", {}).get("task_id", "")
if not task_id:
    print("ERROR: No task_id in response")
    exit(1)

print(f"\nWaiting for task completion (task_id={task_id})...")
for i in range(30):
    time.sleep(2)
    # Check progress
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
                print(f"\n=== STDERR ===\n{stderr}")
            break
        else:
            print(f"  [{i+1}/30] Status: {status}")
    except Exception as e:
        print(f"  Check failed: {e}")
