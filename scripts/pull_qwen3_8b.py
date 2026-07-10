#!/usr/bin/env python3
"""Try pulling qwen3:8b from Chinese mirror"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
$result = & $ollama pull qwen3:8b 2>&1
if ($LASTEXITCODE -eq 0) { Write-Output "SUCCESS" } else { Write-Output "FAILED" }
Write-Output "---"
Write-Output $result
''', timeout=600)
print("=== qwen3:8b pull ===")
print(r.get('stdout',''))
print("stderr:", r.get('stderr',''))
print("exit_code:", r.get('exit_code',''))
