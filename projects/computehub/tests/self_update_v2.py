#!/usr/bin/env python3
"""
ComputeHub Worker 自更新任务 v2
===============================
用 PowerShell 下载新二进制 + START 启动后台清理脚本。
"""

import requests, json, time, sys, uuid

GATEWAY = "http://192.168.1.7:8282"
NODE_ID = "cqf-worker-02"
OLD_PID = 12372

def submit(task_id, command, timeout=60):
    r = requests.post(f"{GATEWAY}/api/v1/tasks/submit", json={
        "task_id": task_id, "node_id": NODE_ID,
        "command": command, "timeout_seconds": timeout, "priority": 8
    }, timeout=10)
    return r.json()

def wait_result(task_id, max_wait=120, interval=5):
    for i in range(max_wait // interval):
        time.sleep(interval)
        r = requests.get(f"{GATEWAY}/api/v1/tasks/detail",
            params={"task_id": task_id, "node_id": NODE_ID}, timeout=10)
        d = r.json()
        if d.get("success"):
            data = d.get("data", {})
            if data.get("status") == "completed":
                return data
            if data.get("status") in ("failed", "error"):
                return data
    return None

def main():
    print("=" * 55)
    print("  ComputeHub Worker 自更新 v2")
    print(f"  目标: {NODE_ID} (PID {OLD_PID})")
    print("=" * 55)

    # 用临时 PS1 脚本文件，避免 shell 转义噩梦
    # Worker 通过 cmd /c 执行 -> 调用 powershell -File 执行 .ps1
    # .ps1 内容：下载 + 启动新Worker + 清理脚本

    # 写入 cleanup.cmd（延迟 20 秒后执行）
    cleanup_ps1 = f"""
$pidToKill = {OLD_PID}
Start-Sleep -Seconds 20

Write-Host "=== Cleanup: Killing old PID $pidToKill ==="
Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
Write-Host "Old process killed"

if (Test-Path D:\\computehub-worker.exe) {{
    Move-Item D:\\computehub-worker.exe D:\\computehub-worker-backup.exe -Force
    Write-Host "Old binary backed up"
}}

Move-Item D:\\computehub-worker-new.exe D:\\computehub-worker.exe -Force
Write-Host "New binary in place"
Write-Host "Cleanup complete"
""".strip()

    # 主更新命令
    main_ps1 = f"""
Write-Host "=== Step 1: Download ==="
$url = "{GATEWAY}/api/v1/download?file=compute-worker-win-amd64.exe"
$dest = "D:\\computehub-worker-new.exe"
$wc = New-Object System.Net.WebClient
try {{
    $wc.DownloadFile($url, $dest)
    $size = (Get-Item $dest).Length
    Write-Host "Download OK: $size bytes"
}} catch {{
    Write-Host "Download FAILED: $_"
    exit 1
}}

Write-Host "=== Step 2: Start new worker ==="
$args = "--gw {GATEWAY} --node-id {NODE_ID} --region cn-east --interval 0.5 --heartbeat 10 --concurrent 6"
Start-Process -FilePath "D:\\computehub-worker-new.exe" -ArgumentList $args -WindowStyle Hidden
Write-Host "New worker launched (background)"

Write-Host "=== Step 3: Schedule cleanup ==="
$cleanupScript = @'
{cleanup_ps1}
'@
$cleanupPath = "D:\\cleanup_worker.ps1"
$cleanupScript | Out-File -FilePath $cleanupPath -Encoding ASCII
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -File $cleanupPath" -WindowStyle Hidden
Write-Host "Cleanup scheduled (will run in 20s)"
Write-Host "=== Self-update triggered ==="
""".strip()

    # 用一个 ps1 文件包含所有逻辑，避免命令行转义
    ps1_content = f"""
# ComputeHub Worker Self-Update

Write-Host "=== ComputeHub Worker Self-Update ==="
Write-Host ""

# Step 1: Download
Write-Host "=== [1/3] Download new binary ==="
$url = "{GATEWAY}/api/v1/download?file=compute-worker-win-amd64.exe"
$dest = "D:\\computehub-worker-new.exe"

try {{
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($url, $dest)
    $size = (Get-Item $dest).Length
    Write-Host "  Download OK: $size bytes ($([math]::Round($size/1MB,2)) MB)"
}} catch {{
    Write-Host "  Download FAILED: $_"
    exit 1
}}

# Step 2: Verify
if (-not (Test-Path $dest)) {{
    Write-Host "  File not found after download!"
    exit 1
}}
if ((Get-Item $dest).Length -lt 1MB) {{
    Write-Host "  File too small, may be corrupt"
    exit 1
}}
Write-Host "  File verified"

# Step 3: Start new worker
Write-Host "=== [2/3] Start new worker ==="
$newArgs = "--gw {GATEWAY} --node-id {NODE_ID} --region cn-east --interval 0.5 --heartbeat 10 --concurrent 6"
Start-Process -FilePath $dest -ArgumentList $newArgs -WindowStyle Hidden
Write-Host "  New worker launched (PID: background process)"

# Step 4: Create and launch delayed cleanup
Write-Host "=== [3/3] Create cleanup script ==="
$cleanupContent = @"
`$pidToKill = $($env:COMPUTERNAME -eq 'LAPTOP-QOVCUVAG' ? $OLD_PID : 0)
Write-Host "=== Cleanup Script ==="
Start-Sleep -Seconds 20
Write-Host "[1/3] Killing old PID: `$pidToKill"
Stop-Process -Id `$pidToKill -Force -ErrorAction SilentlyContinue
Write-Host "  Old process terminated"
if (Test-Path D:\\computehub-worker.exe) {{
    Move-Item D:\\computehub-worker.exe D:\\computehub-worker-backup.exe -Force
    Write-Host "[2/3] Old binary backed up"
}}
Move-Item D:\\computehub-worker-new.exe D:\\computehub-worker.exe -Force
Write-Host "[3/3] New binary in place"
Write-Host "=== Cleanup Complete ==="
"@

$cleanupPath = "D:\\cleanup_worker.ps1"
$cleanupContent | Out-File -FilePath $cleanupPath -Encoding ASCII
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File $cleanupPath" -WindowStyle Hidden
Write-Host "  Cleanup scheduled (20s delay, background)"
Write-Host ""
Write-Host "=== Self-update complete ==="
""".strip()

    # 写入临时文件并通过 PowerShell -File 执行
    # 注意：Worker 执行时当前目录在 D:\，所以写 D:\update.ps1 没问题
    ps1_encoded = ps1_content.replace('"', '\\"')
    cmd = (
        'cmd /c '
        'echo ' + ps1_content.replace('\n', ' & echo ') + ' > D:\\update.ps1'
        ' & powershell -NoProfile -ExecutionPolicy Bypass -File D:\\update.ps1'
    )

    tid = "update-" + str(int(time.time()))
    print(f"\nTask: {tid}")
    print(f"PS1 length: {len(ps1_content)} chars")

    r = submit(tid, cmd, timeout=60)
    print(f"Submit: {r}")

    print("Waiting for result (max 60s)...")
    result = wait_result(tid, max_wait=60)

    if result:
        print(f"\nTask complete: exit={result.get('exit_code')}")
        stdout = result.get("stdout", "")
        if stdout:
            for line in stdout.split("\n"):
                line = line.strip()
                if line:
                    print(f"  {line}")
        stderr = result.get("stderr", "")
        if stderr:
            print(f"  [stderr] {stderr[:300]}")
    else:
        print("Task timed out or no result")

    print("\nChecking node list...")
    time.sleep(5)
    r = requests.get(f"{GATEWAY}/api/v1/nodes/list", timeout=10)
    if r.json().get("success"):
        nodes = r.json().get("data", [])
        print(f"Online nodes: {len(nodes)}")
        for n in nodes:
            print(f"  {n['node_id']}: {n['status']}")

if __name__ == "__main__":
    main()
