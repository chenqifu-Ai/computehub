#!/usr/bin/env python3
"""
Unified disk IO test - 2026-05-14
Both nodes: 5x 10MB write (forced flush) + read test
"""

import json
import time
import urllib.request
import base64

GW = "http://192.168.1.12:8282"

# ===== Fedora: 5x 10MB with fdatasync =====
fedora_cmd = """
echo "=== Fedora Disk IO (2026-05-14) ==="
echo "Write 5x 10MB with fdatasync (forced flush)..."
total_write=0
for i in 1 2 3 4 5; do
    start=$(date +%s%N)
    dd if=/dev/zero of=/tmp/fedora_test_${i}.bin bs=1M count=10 conv=fdatasync 2>/dev/null
    end=$(date +%s%N)
    ms=$(( (end - start) / 1000000 ))
    echo "  Write ${i}/5: ${ms}ms"
    total_write=$((total_write + ms))
done
echo "  Total write (forced): ${total_write}ms"

echo ""
echo "Read 10MB..."
dd if=/tmp/fedora_test_1.bin of=/dev/null bs=1M 2>&1
echo "Read done"

rm -f /tmp/fedora_test_*.bin
echo ""
echo "=== Fedora Complete ==="
"""

# ===== Windows: 5x 10MB with Flush (forced flush) =====
ps_script = r'''
Write-Host "=== Windows Disk IO (2026-05-14) ==="
Write-Host "Write 5x 10MB with Flush (forced flush)..."
$totalWriteMs = 0
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$data = [byte[]]::new(10485760)  # 10MB
[System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($data)

for ($i = 1; $i -le 5; $i++) {
    $stopwatch.Reset()
    $stopwatch.Start()
    $file = "D:\testdisk\win_test_${i}.bin"
    if (-not (Test-Path D:\testdisk)) { New-Item -ItemType Directory -Path D:\testdisk -Force | Out-Null }
    $stream = [System.IO.File]::OpenWrite($file)
    $stream.Write($data, 0, $data.Length)
    $stream.Flush($true)  # True = flush to disk, not just buffer
    $stream.Close()
    $stopwatch.Stop()
    Write-Host "  Write ${i}/5: $($stopwatch.ElapsedMilliseconds)ms"
    $totalWriteMs = $totalWriteMs + $stopwatch.ElapsedMilliseconds
}
Write-Host "  Total write (forced): ${totalWriteMs}ms"

Write-Host ""
Write-Host "Read 10MB..."
$stopwatch.Reset()
$stopwatch.Start()
$rstream = [System.IO.File]::OpenRead("D:\testdisk\win_test_1.bin")
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
Write-Host "$([math]::Round($readMB,2))MB read: $($stopwatch.ElapsedMilliseconds)ms"

Get-ChildItem D:\testdisk -Filter "win_test_*.bin" | Remove-Item -Force
Write-Host ""
Write-Host "=== Windows Complete ==="
'''

b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
windows_cmd = f"powershell -EncodedCommand {b64}"

results = {}

# ===== Run Fedora =====
print("=" * 60)
print("FEDORA TEST (fdatasync)")
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
print(f"Fedora task: {fedora_task_id}")

for i in range(60):
    time.sleep(2)
    try:
        req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={fedora_task_id}")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        detail = json.loads(resp2.read())
        if detail["data"]["status"] in ("completed", "failed", "error"):
            results["fedora"] = detail["data"].get("stdout", "")
            break
    except:
        pass

# ===== Run Windows =====
print("\n" + "=" * 60)
print("WINDOWS TEST (Flush=true)")
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
print(f"Windows task: {windows_task_id}")

for i in range(60):
    time.sleep(2)
    try:
        req2 = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={windows_task_id}")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        detail = json.loads(resp2.read())
        if detail["data"]["status"] in ("completed", "failed", "error"):
            results["windows"] = detail["data"].get("stdout", "")
            break
    except:
        pass

# ===== Print comparison =====
print("\n" + "=" * 60)
print("COMPARISON (2026-05-14)")
print("=" * 60)

for name, output in [("Fedora", results["fedora"]), ("Windows", results["windows"])]:
    print(f"\n--- {name} ---")
    print(output.strip().replace("\n", "\n  "))
