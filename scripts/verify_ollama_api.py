#!/usr/bin/env python3
"""Verify ollama API and list models on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check API
r1 = cluster_exec('wanlida-work01', '''
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 10
    Write-Output "API Status: $($resp.StatusCode)"
    Write-Output $resp.Content
} catch {
    Write-Output "API error: $_"
}
''', timeout=20)
print("=== API Tags ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))

# Check version
r2 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$ver = & $ollama --version 2>&1
Write-Output "version: $ver"
''', timeout=10)
print("\n=== Version ===")
print(r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))
