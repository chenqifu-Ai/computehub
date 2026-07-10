#!/usr/bin/env python3
"""Check qwen3 availability on mirror and try to pull"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Try qwen3:4b (smallest, ~2.5GB)
r = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
$result = & $ollama pull qwen3:4b 2>&1
if ($LASTEXITCODE -eq 0) { Write-Output "AVAILABLE" } else { Write-Output "NOT_AVAILABLE" }
''', timeout=120)
print("=== qwen3:4b ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
