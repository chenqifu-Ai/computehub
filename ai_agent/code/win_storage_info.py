#!/usr/bin/env python3
"""Check Windows node storage type - SSD, HDD, or RAM disk"""

import json
import time
import base64
import urllib.request

GW = "http://192.168.1.12:8282"

ps_script = r'''
# 1. Check disk type (SSD vs HDD)
Write-Host "=== Physical Disk Info ==="
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, Size | Format-Table -AutoSize

Write-Host ""
Write-Host "=== Volume Info ==="
Get-Volume | Where-Object DriveLetter -eq "D" | Select-Object DriveLetter, FileSystemLabel, FileSystem, SizeRemaining, Size | Format-Table -AutoSize

Write-Host ""
Write-Host "=== D:\ Drive Info ==="
$vol = Get-Volume -DriveLetter D
$drive = Get-CimInstance Win32_DiskDrive | Where-Object InterfaceType -eq "USB" -or $_.InterfaceType -eq "SCSI" -or $_.InterfaceType -eq "ATA"
Get-Partition | Select-Object DiskNumber, DriveLetter, Type, @{N="SizeGB";E={[math]::Round($_.Size/1GB,2)}} | Format-Table -AutoSize

Write-Host ""
Write-Host "=== Quick benchmark: 100MB with Flush ==="
$testDir = "D:\testdisk"
if (-not (Test-Path $testDir)) { New-Item -ItemType Directory -Path $testDir -Force | Out-Null }
$testFile = Join-Path $testDir "bench_test.bin"
$bigData = [byte[]]::new(104857600)  # 100MB
[System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($bigData)

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$stream = [System.IO.File]::OpenWrite($testFile)
$stream.Write($bigData, 0, $bigData.Length)
$stream.Flush($true)  # Force to disk
$stream.Close()
$sw.Stop()
Write-Host "100MB write with Flush: $($sw.ElapsedMilliseconds)ms"

$sw.Reset()
$sw.Start()
$rstream = [System.IO.File]::OpenRead($testFile)
$buffer = [byte[]]::new(104857600)
$totalRead = 0
while ($true) {
    $bytesRead = $rstream.Read($buffer, 0, $buffer.Length)
    if ($bytesRead -eq 0) { break }
    $totalRead += $bytesRead
}
$rstream.Close()
$sw.Stop()
$readMB = $totalRead / (1024*1024)
Write-Host "$([math]::Round($readMB,2))MB read: $($sw.ElapsedMilliseconds)ms"

Remove-Item $testFile -Force
Write-Host "=== Done ==="
'''

b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
cmd = f"powershell -EncodedCommand {b64}"

print("Submitting Windows storage info test...")

payload = {"command": cmd, "node_id": "worker-DESKTOP-BUAUIFL"}
req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())

task_id = result["data"]["task_id"]
print(f"Task ID: {task_id}")

for i in range(60):
    time.sleep(2)
    try:
        req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        detail = json.loads(resp2.read())
        if detail["data"]["status"] in ("completed", "failed", "error"):
            stdout = detail["data"].get("stdout", "")
            print(f"\n=== STDOUT ===\n{stdout}")
            stderr = detail["data"].get("stderr", "")
            if stderr:
                print(f"\n=== STDERR ===\n{stderr[:500]}")
            break
    except:
        pass
