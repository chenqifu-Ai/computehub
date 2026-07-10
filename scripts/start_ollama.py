#!/usr/bin/env python3
"""Start ollama service on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$log = "$env:USERPROFILE\\ollama\\ollama.log"

Write-Output "=== Starting ollama ==="
$env:OLLAMA_HOST = "0.0.0.0"
$env:OLLAMA_ORIGINS = "*"
$env:OLLAMA_KEEP_ALIVE = "24h"

# Start in background
$proc = Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError "${log}.err" -PassThru
Start-Sleep 3

# Check
$running = Get-Process ollama -ErrorAction SilentlyContinue
if ($running) {
    Write-Output "ollama started: PID=$($running.Id)"
} else {
    Write-Output "ollama failed to start"
    if (Test-Path $log) { Write-Output "=== log ==="; Get-Content $log -Tail 10 }
    if (Test-Path "${log}.err") { Write-Output "=== err ==="; Get-Content "${log}.err" -Tail 10 }
}

# Verify API
Start-Sleep 2
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    Write-Output "API: $($resp.StatusCode)"
} catch {
    Write-Output "API not ready yet"
}
''', timeout=30)
print("=== Start ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
