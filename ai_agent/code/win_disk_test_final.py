#!/usr/bin/env python3
"""
Windows disk IO test - clean approach.
Worker wrapper: exec.Command("cmd", "/c", "chcp 65001 >nul && <cmd>")
Strategy: Use PowerShell -EncodedCommand with UTF-16LE encoding.
The base64 string contains ONLY [A-Za-z0-9+/=] which are all safe for cmd.exe.
"""

import json
import base64
import time
import urllib.request

GW = "http://192.168.1.12:8282"

# Step 1: Build a simple PowerShell script
ps_lines = [
    r'$testDir = "D:\testdisk"',
    r'$testFile = Join-Path $testDir "testfile.bin"',
    r'if (-not (Test-Path $testDir)) { New-Item -ItemType Directory -Path $testDir -Force | Out-Null }',
    r'',
    r'Write-Host "=== Disk Write Test (50MB) ==="',
    r'$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()',
    r'$data = [byte[]]::new(10485760)',
    r'[System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($data)',
    r'$stream = [System.IO.File]::OpenWrite($testFile)',
    r'for ($i = 0; $i -lt 5; $i++) { $stream.Write($data, 0, $data.Length) }',
    r'$stream.Close()',
    r'$stopwatch.Stop()',
    r'Write-Host "50MB sequential write: $($stopwatch.ElapsedMilliseconds)ms"',
    r'',
    r'Write-Host "=== Disk Read Test ==="',
    r'$stopwatch.Reset()',
    r'$stopwatch.Start()',
    r'$rstream = [System.IO.File]::OpenRead($testFile)',
    r'$buffer = [byte[]]::new(10485760)',
    r'$totalRead = 0',
    r'while ($true) {',
    r'    $bytesRead = $rstream.Read($buffer, 0, $buffer.Length)',
    r'    if ($bytesRead -eq 0) { break }',
    r'    $totalRead += $bytesRead',
    r'}',
    r'$rstream.Close()',
    r'$stopwatch.Stop()',
    r'$readMB = $totalRead / (1024*1024)',
    r'Write-Host "$([math]::Round($readMB,2))MB sequential read: $($stopwatch.ElapsedMilliseconds)ms"',
    r'',
    r'Remove-Item $testFile -Force',
    r'Write-Host "=== Disk IO Test Complete ==="',
]

ps_script = "\n".join(ps_lines)
print(f"PS script length: {len(ps_script)} chars")

# Step 2: Base64 encode for PowerShell -EncodedCommand (needs UTF-16LE)
b64_str = base64.b64encode(ps_script.encode("utf-16-le")).decode("ascii")
print(f"Base64 string length: {len(b64_str)} chars")

# Step 3: The full command before cmd wrapping
full_cmd = f"powershell -EncodedCommand {b64_str}"
print(f"Full command length: {len(full_cmd)} chars (under 8191 limit: {len(full_cmd) < 8191})")

# Step 4: Submit to Windows worker
payload = {
    "command": full_cmd,
    "node_id": "worker-DESKTOP-BUAUIFL",
}

print(f"\nSubmitting to {GW}/api/v1/tasks/submit")

req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print(f"Submit result: success={result.get('success')}")
if not result.get("success"):
    print(f"Error: {result.get('error')}")
    exit(1)

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
                print(f"\n--- STDERR ---\n{stderr[:1000]}")
            break
        else:
            print(f"  [{i+1}/60] Status: {status}")
    except Exception as e:
        print(f"  Check failed: {e}")
