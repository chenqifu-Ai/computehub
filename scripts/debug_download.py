#!/usr/bin/env python3
"""Debug download issue and try alternative methods"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Check connectivity to Gallery
r1 = cluster_exec('wanlida-work01', '''
Write-Output "=== Test Gallery connectivity ==="
try {
    $resp = Invoke-WebRequest -Uri "http://36.250.122.43:8282/" -UseBasicParsing -TimeoutSec 10
    Write-Output "Gateway root: $($resp.StatusCode) $($resp.ContentLength)"
} catch { Write-Output "Gateway root FAIL: $_" }

try {
    $resp = Invoke-WebRequest -Uri "http://36.250.122.43:8282/api/v1/files/" -UseBasicParsing -TimeoutSec 10
    Write-Output "Gallery list: $($resp.StatusCode) $($resp.ContentLength)"
} catch { Write-Output "Gallery list FAIL: $_" }

try {
    $resp = Invoke-WebRequest -Uri "http://36.250.122.43:8282/api/v1/files/ollama-windows-v0.6.2.zip" -UseBasicParsing -TimeoutSec 10
    Write-Output "File check: $($resp.StatusCode) $($resp.ContentLength)"
} catch { Write-Output "File check FAIL: $_" }
''', timeout=30)
print("=== Connectivity ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
