#!/usr/bin/env python3
"""Try to pull qwen3:8b directly from ollama registry (not mirror)"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"

# Try without mirror (direct to ollama registry)
Write-Output "=== Try direct pull (no mirror) ==="
$env:OLLAMA_BASE_URL = ""
$result = & $ollama pull qwen3:8b 2>&1
if ($LASTEXITCODE -eq 0) { Write-Output "SUCCESS" } else { Write-Output "FAILED" }
Write-Output $result
''', timeout=600)
print("=== Direct pull ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
