#!/usr/bin/env python3
"""Start ollama service on wanlida-work01 and configure proxy"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Start ollama service in background
r1 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$log = "$env:USERPROFILE\\ollama\\ollama.log"
# Kill any existing process first
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1
# Start ollama with proxy env vars
$env:OLLAMA_HOST = "0.0.0.0"
$env:OLLAMA_ORIGINS = "*"
$env:OLLAMA_KEEP_ALIVE = "24h"
Start-Process -FilePath $ollama -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError "${log}.err"
Start-Sleep 3
# Check if running
$proc = Get-Process ollama -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "ollama started: PID=$($proc.Id)"
} else {
    Write-Output "ollama failed to start"
    if (Test-Path $log) { Write-Output "=== log ==="; Get-Content $log -Tail 10 }
}
''', timeout=20)
print("=== Start Ollama ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))

# Step 2: Verify it's running
r2 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$ver = & $ollama --version 2>&1
Write-Output "version: $ver"
# Check API
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    Write-Output "API: $($resp.StatusCode)"
    Write-Output $resp.Content
} catch {
    Write-Output "API error: $_"
}
''', timeout=20)
print("\n=== Verify ===")
print(r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))
