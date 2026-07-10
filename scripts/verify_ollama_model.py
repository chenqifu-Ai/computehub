#!/usr/bin/env python3
"""Verify model and test inference on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check models list
r1 = cluster_exec('wanlida-work01', '''
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 10
    Write-Output $resp.Content
} catch { Write-Output "API error: $_" }
''', timeout=15)
print("=== Models ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))

# Test inference
r2 = cluster_exec('wanlida-work01', '''
try {
    $body = @{model="qwen2.5:0.5b"; prompt="你好，用中文回答：1+1=?"; stream=$false} | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 30
    $data = $resp.Content | ConvertFrom-Json
    Write-Output "response: $($data.response)"
    Write-Output "duration: $($data.total_duration) ns"
} catch { Write-Output "API error: $_" }
''', timeout=45)
print("\n=== Inference Test ===")
print(r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))
