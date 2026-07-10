#!/usr/bin/env python3
"""Check ollama service and models on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check if ollama service is running
r1 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
if (Test-Path $ollama) {
    Write-Output "ollama.exe exists at: $ollama"
    # Check if process is running
    $proc = Get-Process ollama -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "ollama process running: PID=$($proc.Id) CPU=$([math]::Round($proc.CPU,1))s"
    } else {
        Write-Output "ollama process NOT running"
    }
    # Check version
    $ver = & $ollama --version 2>&1
    Write-Output "version: $ver"
} else {
    Write-Output "ollama.exe not found"
}
''', timeout=15)
print("=== Service Status ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))

# Check models
r2 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
if (Test-Path $ollama) {
    $models = & $ollama list 2>&1
    Write-Output "Models:"
    Write-Output $models
}
''', timeout=30)
print("\n=== Models ===")
print(r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))
