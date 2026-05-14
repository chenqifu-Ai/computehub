#!/usr/bin/env python3
"""
Windows disk IO test - step by step approach without base64.
The cmd wrapper does: cmd /c "chcp 65001 >nul && <cmd>"
We need commands with NO quotes, NO special chars (no >, |, &, <, etc.)
"""

import json
import time
import urllib.request

GW = "http://192.168.1.12:8282"

# Approach: Write PS1 file using a series of simple echo commands (no special chars), then run it
# Actually, let's try the simplest thing first: just use PowerShell directly
# But cmd wrapper will mangle things...

# Let me try: write the script as hex dump, then convert
# Or even simpler: use PowerShell -NoProfile -NonInteractive and avoid all shell chars

# The PS script has issues: $(), [byte[]], etc. - these all get interpreted by cmd
# Let's use a completely different strategy: write a base64-encoded PS1 file using certutil

# certutil -decodebase64 file.b64 output.ps1  →  this avoids all shell interpretation

# Build the PS script
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

# Base64 encode the PS script (standard base64)
script_b64 = __import__('base64').b64encode(ps_script.encode('utf-8')).decode('ascii')

# Use certutil to decode: certutil -decodebase64 string output
# But we need it in a file first
# certutil -decodebase64 encode.txt output.ps1

# Write the b64 script to a file, then use certutil
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.b64', delete=False) as f:
    f.write(script_b64)
    b64_file = f.name

# cmd: certutil -decodebase64 {b64_file} C:\test.ps1 && powershell -File C:\test.ps1
# But we need the b64 file on Windows...

# SIMPLER: Use PowerShell -EncodedCommand with the right encoding
# The issue with previous attempts: worker does exec.Command("cmd", "/c", "chcp 65001 >nul && <cmd>")
# When cmd parses "chcp 65001 >nul && powershell -EncodedCommand XXX", it should work fine
# The >nul redirects chcp output, && chains to powershell

# Let me check: maybe the issue is that the base64 string contains characters that cmd interprets
# base64 uses A-Za-z0-9+/= - these should all be safe for cmd

# Actually, the previous failure was about $() in the PS script being interpreted
# with -EncodedCommand, the whole command is base64, so $() shouldn't be interpreted by cmd

# Let me re-examine: the FIRST attempt used base64 and got error about '_x000D__x000A_'
# which suggests the base64 string was CORRECT but PowerShell had a parse error at line 25: break

# The SECOND attempt (win_disk_test2) used -EncodedCommand and got:
# "Missing statement block after if ( condition )." at line 25 "if ($bytesRead -eq 0) break"
# This means PowerShell WAS running but the -eq 0 part was being interpreted wrong

# Wait - in the worker_util_windows.go, the command is:
# exec.Command("cmd", "/c", "chcp 65001 >nul && "+cmd)
# If cmd is the base64 encoded command "powershell -EncodedCommand XXX", 
# cmd.exe should just pass XXX to powershell -EncodedCommand

# BUT: if the base64 string is too long, cmd might truncate it!
# Command line limit for cmd.exe is typically 8191 chars

# Let me check the length of our encoded command
print(f"Script length: {len(ps_script)}")
print(f"Base64 length: {len(script_b64)}")
full_cmd = f"powershell -EncodedCommand {script_b64}"
print(f"Full command length: {len(full_cmd)}")
# 3160 chars for base64 + ~22 for "powershell -EncodedCommand " = ~3182
# Then cmd wrapper adds ~25 chars = ~3207
# This should be under 8191...

# Let me try with PowerShell using the script directly without base64
# Use a simpler approach: write the script to a file using base64, then execute

# Step 1: base64 encode and decode to write file, then execute
b64_cmd = f'powershell -Command "[$b]=\\'{script_b64}\\'; [IO.File]::WriteAllText(\\'C:\\\\test.ps1\\',[System.Convert]::FromBase64String(\\'\\')  # This won't work either

# NEW APPROACH: Just test if Windows worker can execute ANY simple command first
simple_cmd = "powershell -NoProfile -Command Get-ComputerInfo | Select-Object WindowsProductName,OSEdition,WindowsVersion"

payload = {
    "command": simple_cmd,
    "node_id": "worker-DESKTOP-BUAUIFL"
}

print(f"\nFirst, testing simple command to Windows node...")
print(f"Command: {simple_cmd}")

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
