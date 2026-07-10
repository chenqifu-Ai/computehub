#!/usr/bin/env python3
"""Restart ollama on wanlida-work01 and test"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Check status
r1 = cluster_exec('wanlida-work01', '''
Write-Output "=== Process check ==="
$proc = Get-Process ollama -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "ollama running: PID=$($proc.Id)"
} else {
    Write-Output "ollama NOT running"
}

Write-Output "=== Port check ==="
try {
    $conn = Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue
    if ($conn) { Write-Output "Port 11434: LISTENING" } else { Write-Output "Port 11434: NOT LISTENING" }
} catch { Write-Output "Port check failed" }
''', timeout=15)
print("=== Status ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
