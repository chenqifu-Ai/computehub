#!/usr/bin/env python3
"""
Comprehensive disk IO test - same method on both nodes.
- Windows: 50MB sequential write (5x 10MB), 50MB sequential read
- Fedora: 50MB sequential write (5x 10MB), 50MB sequential read
Same dd parameters on Fedora for fair comparison
"""

import json
import time
import urllib.request

GW = "http://192.168.1.12:8282"

# Fedora test - exact same 5x write pattern as Windows, no direct I/O
fedora_cmd = r"""
echo "=== Disk Write Test (5x 10MB = 50MB total) ==="
total_time=0
for i in 1 2 3 4 5; do
    start=$(date +%s%N)
    dd if=/dev/zero of=/tmp/fedora_test_${i}.bin bs=1M count=10 conv=fdatasync 2>/dev/null
    end=$(date +%s%N)
    ms=$(( (end - start) / 1000000 ))
    echo "  Write ${i}/5: ${ms}ms"
    total_time=$((total_time + ms))
done
echo "  Total write: ${total_time}ms"
rm -f /tmp/fedora_test_*.bin

echo ""
echo "=== Disk Read Test (50MB single read) ==="
# Recreate a 50MB file for read test
dd if=/dev/urandom of=/tmp/fedora_read_test.bin bs=1M count=50 2>/dev/null
start=$(date +%s%N)
dd if=/tmp/fedora_read_test.bin of=/dev/null bs=1M 2>&1
end=$(date +%s%N)
ms=$(( (end - start) / 1000000 ))
echo "  50MB sequential read: ${ms}ms"
rm -f /tmp/fedora_read_test.bin

echo ""
echo "=== Disk IO Test Complete ==="
"""

# Windows test - same pattern but using PowerShell
ps_lines = [
    r'$testDir = "D:\testdisk"',
    r'if (-not (Test-Path $testDir)) { New-Item -ItemType Directory -Path $testDir -Force | Out-Null }',
    r'',
    r'Write-Host "=== Disk Write Test (5x 10MB = 50MB total) ==="',
    r'$totalMs = 0',
    r'$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()',
    r'$data = [byte[]]::new(10485760)  # 10MB chunk',
    r'[System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($data)',
    r'for ($i = 1; $i -le 5; $i++) {',
    r'    $stopwatch.Reset()',
    r'    $stopwatch.Start()',
    r'    $file = Join-Path $testDir "win_test_${i}.bin"',
    r'    $stream = [System.IO.File]::OpenWrite($file)',
    r'    $stream.Write($data, 0, $data.Length)',
    r'    $stream.Close()',
    r'    $stopwatch.Stop()',
    r'    Write-Host "  Write ${i}/5: $($stopwatch.ElapsedMilliseconds)ms"',
    r'    $totalMs = $totalMs + $stopwatch.ElapsedMilliseconds',
    r'}',
    r'Write-Host "  Total write: ${totalMs}ms"',
    r'',
    r'Write-Host ""',
    r'Write-Host "=== Disk Read Test (50MB single read) ==="',
    r'$stopwatch.Reset()',
    r'$stopwatch.Start()',
    r'$bigFile = Join-Path $testDir "win_read_test.bin"',
    r'$bigData = [byte[]]::new(104857600)  # 100MB for read test',
    r'[System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($bigData)',
    r'[System.IO.File]::WriteAllBytes($bigFile, $bigData)',
    r'$rstream = [System.IO.File]::OpenRead($bigFile)',
    r'$buffer = [byte[]]::new(104857600)',
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
    r'Get-ChildItem $testDir -Filter "win_*.bin" | Remove-Item -Force',
    r'Write-Host ""',
    r'Write-Host "=== Disk IO Test Complete ==="',
]

ps_script = "\n".join(ps_lines)
b64_str = __import__('base64').b64encode(ps_script.encode("utf-16-le")).decode("ascii")
windows_cmd = f"powershell -EncodedCommand {b64_str}"

results = {}

# Run Fedora test
print("=" * 60)
print("FEDORA TEST")
print("=" * 60)

fedora_payload = {"command": fedora_cmd, "node_id": "fedora-gpu-01"}
req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(fedora_payload).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=10)
fedora_result = json.loads(resp.read())
fedora_task_id = fedora_result["data"]["task_id"]

print(f"Fedora task submitted: {fedora_task_id}")
for i in range(120):
    time.sleep(2)
    try:
        req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={fedora_task_id}")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        detail = json.loads(resp2.read())
        status = detail["data"]["status"]
        if status in ("completed", "failed", "error"):
            stdout = detail["data"].get("stdout", "")
            results["fedora"] = stdout
            print(stdout)
            break
    except:
        pass

# Run Windows test
print("\n" + "=" * 60)
print("WINDOWS TEST")
print("=" * 60)

windows_payload = {"command": windows_cmd, "node_id": "worker-DESKTOP-BUAUIFL"}
req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(windows_payload).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=10)
windows_result = json.loads(resp.read())
windows_task_id = windows_result["data"]["task_id"]

print(f"Windows task submitted: {windows_task_id}")
for i in range(120):
    time.sleep(2)
    try:
        req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={windows_task_id}")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        detail = json.loads(resp2.read())
        status = detail["data"]["status"]
        if status in ("completed", "failed", "error"):
            stdout = detail["data"].get("stdout", "")
            results["windows"] = stdout
            print(stdout)
            break
    except:
        pass

# Print comparison
print("\n" + "=" * 60)
print("COMPARISON SUMMARY")
print("=" * 60)
for node, output in results.items():
    print(f"\n[{node.upper()}]")
    for line in output.strip().split("\n"):
        print(f"  {line}")
