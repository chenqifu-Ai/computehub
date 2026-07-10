#!/usr/bin/env python3
"""Test ollama with Chinese mirror/proxy on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Test 1: Check internet connectivity
r1 = cluster_exec('wanlida-work01', '''
try {
    $resp = Invoke-WebRequest -Uri "https://www.baidu.com" -UseBasicParsing -TimeoutSec 10
    Write-Output "baidu: $($resp.StatusCode)"
} catch { Write-Output "baidu: FAIL - $_" }
try {
    $resp = Invoke-WebRequest -Uri "https://modelscope.cn" -UseBasicParsing -TimeoutSec 10
    Write-Output "modelscope: $($resp.StatusCode)"
} catch { Write-Output "modelscope: FAIL - $_" }
try {
    $resp = Invoke-WebRequest -Uri "https://registry.ollama.ai" -UseBasicParsing -TimeoutSec 10
    Write-Output "ollama-registry: $($resp.StatusCode)"
} catch { Write-Output "ollama-registry: FAIL - $_" }
''', timeout=30)
print("=== Connectivity ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))

# Test 2: Try pulling a small model with proxy
r2 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
# Try with HTTP_PROXY set (common Chinese proxy)
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$result = & $ollama pull qwen2.5:0.5b 2>&1
Write-Output "pull result: $result"
''', timeout=60)
print("\n=== Pull Test (no proxy) ===")
print(r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))
