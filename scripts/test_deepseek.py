#!/usr/bin/env python3
"""Test deepseek-r1:7b inference on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Test 1: Basic Chinese QA
r1 = cluster_exec('wanlida-work01', '''
try {
    $body = @{
        model="deepseek-r1:7b"
        prompt="请用中文回答：中国的首都是哪里？介绍一下这个城市。"
        stream=$false
    } | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 120
    $data = $resp.Content | ConvertFrom-Json
    Write-Output "=== 测试1：中文问答 ==="
    Write-Output "回答: $($data.response)"
    Write-Output "耗时: $([math]::Round($data.total_duration/1e9,2))s"
    Write-Output "Token数: $($data.eval_count)"
    Write-Output "速度: $([math]::Round($data.eval_count / ($data.eval_duration/1e9),1)) tokens/s"
} catch { Write-Output "FAIL: $_" }
''', timeout=180)
print(r1.get('stdout',''))
print("---")

# Test 2: Code generation
r2 = cluster_exec('wanlida-work01', '''
try {
    $body = @{
        model="deepseek-r1:7b"
        prompt="Write a Python function to check if a string is a palindrome. Include comments."
        stream=$false
    } | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 120
    $data = $resp.Content | ConvertFrom-Json
    Write-Output "=== 测试2：代码生成 ==="
    Write-Output "回答: $($data.response)"
    Write-Output "耗时: $([math]::Round($data.total_duration/1e9,2))s"
    Write-Output "Token数: $($data.eval_count)"
    Write-Output "速度: $([math]::Round($data.eval_count / ($data.eval_duration/1e9),1)) tokens/s"
} catch { Write-Output "FAIL: $_" }
''', timeout=180)
print(r2.get('stdout',''))
print("---")

# Test 3: Math reasoning
r3 = cluster_exec('wanlida-work01', '''
try {
    $body = @{
        model="deepseek-r1:7b"
        prompt="请一步步推理：一个水池，甲管单独注水需要6小时注满，乙管单独注水需要8小时注满。如果两管同时开，需要多少小时注满？"
        stream=$false
    } | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 120
    $data = $resp.Content | ConvertFrom-Json
    Write-Output "=== 测试3：数学推理 ==="
    Write-Output "回答: $($data.response)"
    Write-Output "耗时: $([math]::Round($data.total_duration/1e9,2))s"
    Write-Output "Token数: $($data.eval_count)"
    Write-Output "速度: $([math]::Round($data.eval_count / ($data.eval_duration/1e9),1)) tokens/s"
} catch { Write-Output "FAIL: $_" }
''', timeout=180)
print(r3.get('stdout',''))
