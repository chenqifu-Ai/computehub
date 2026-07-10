#!/usr/bin/env python3
"""Pull deepseek-r1:7b on wanlida-work01 via Chinese mirror"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r1 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
$result = & $ollama pull deepseek-r1:7b 2>&1
Write-Output "pull result: $result"
''', timeout=600)
print("=== Pull deepseek-r1:7b ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))
