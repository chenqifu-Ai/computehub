#!/usr/bin/env python3
"""
Windows disk IO test - using direct base64 PowerShell execution.
The worker wrapper is: cmd /c "chcp 65001 >nul && <cmd>"
But the base64 command gets mangled by cmd. So we encode the ENTIRE command including chcp.
"""

import json
import base64
import time
import urllib.request

GW = "http://192.168.1.12:8282"

# Build a complete PowerShell script that does everything
# We'll base64 encode the FULL command so it bypasses cmd interpretation entirely
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
    if ($bytesRead -eq 0) { break }
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

# PowerShell -EncodedCommand needs UTF-16LE encoding
# Encode the ENTIRE "powershell -EncodedCommand ..." so cmd just runs it
full_cmd = f"powershell -EncodedCommand {base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')}"

# Now encode the FULL command (powershell -EncodedCommand ...) in base64
# So cmd /c gets a simple single-token command
full_b64 = base64.b64encode(full_cmd.encode('utf-16-le')).decode('ascii')

# Use cmd /c but with a simple base64 command that decodes to "powershell -EncodedCommand ..."
# Actually the issue is that when the worker does:
#   exec.Command("cmd", "/c", "chcp 65001 >nul && <cmd>")
# The <cmd> gets embedded and >nul is fine but the && before our command is fine too
# The problem might be the base64 string length or special chars

# Let me try a simpler approach: just write the PS1 file first using base64, then execute it
write_cmd = f'echo {b64_b64} | base64 -d > C:\\test.ps1'

# Actually let me try a totally different approach: use a very simple PowerShell one-liner
# that writes a script file, then executes it

# Step 1: Base64 encode the PS script
script_b64 = base64.b64encode(ps_script.encode('utf-8')).decode('ascii')

# Step 2: Use a simple command to decode and save, then run
# cmd command: powershell -Command "Set-Content -Path C:\\test.ps1 -Value ([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('...'))); powershell -File C:\\test.ps1"

cmd_cmd = f'powershell -Command "Set-Content -Path C:\\\\test.ps1 -Value ([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String(\\"{script_b64}\\"))); powershell -File C:\\\\test.ps1"'

print(f"Command length: {len(cmd_cmd)} chars")
print(f"First 200 chars: {cmd_cmd[:200]}...")

payload = {
    "command": cmd_cmd,
    "node_id": "worker-DESKTOP-BUAUIFL"
}

print(f"\nSubmitting to {GW}/api/v1/tasks/submit")

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
