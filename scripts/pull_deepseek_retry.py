#!/usr/bin/env python3
"""Try pulling deepseek-r1:7b with DNS fix and retry"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# First check DNS
r1 = cluster_exec('wanlida-work01', '''
Resolve-DnsName ollama.mirrors.aidc.space -ErrorAction SilentlyContinue | Select-Object IPAddress
if (-not $?) { Write-Output "DNS_FAIL"; nslookup ollama.mirrors.aidc.space 2>&1 | Select-Object -Last 5 }
''', timeout=10)
print("=== DNS Check ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))

# Try pulling with the mirror that worked for qwen2.5
r2 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
# Flush DNS first
ipconfig /flushdns 2>&1 | Out-Null
Start-Sleep 2
$result = & $ollama pull deepseek-r1:7b 2>&1
Write-Output "pull result: $result"
''', timeout=600)
print("\n=== Pull deepseek-r1:7b (retry) ===")
print(r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))
