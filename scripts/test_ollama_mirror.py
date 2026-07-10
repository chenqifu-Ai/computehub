#!/usr/bin/env python3
"""Try ollama with Chinese mirror and modelscope import"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Test 1: Try ollama pull with OLLAMA_MIRROR env
r1 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
# Try common Chinese ollama mirrors
$env:OLLAMA_HOST = "http://localhost:11434"
# Some ollama builds support OLLAMA_BASE_URL for mirror
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
$result = & $ollama pull qwen2.5:0.5b 2>&1
Write-Output "pull result: $result"
''', timeout=120)
print("=== Mirror Test 1 (aidc.space) ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))
