#!/usr/bin/env python3
"""Verify deepseek-r1:7b inference on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r1 = cluster_exec('wanlida-work01', '''
try {
    $body = @{model="deepseek-r1:7b"; prompt="你好，用中文简单介绍一下你自己"; stream=$false} | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 120
    $data = $resp.Content | ConvertFrom-Json
    Write-Output "response: $($data.response)"
    Write-Output "duration_ns: $($data.total_duration)"
    Write-Output "tokens: $($data.eval_count)"
    $tps = [math]::Round($data.eval_count / ($data.eval_duration/1e9), 1)
    Write-Output "tokens_per_sec: $tps"
} catch { Write-Output "API error: $_" }
''', timeout=180)
print("=== deepseek-r1:7b Inference ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))
