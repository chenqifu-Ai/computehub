#!/usr/bin/env python3
"""Check what models are available on the Chinese mirror"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

models = [
    "qwen3:0.6b",
    "qwen3:1.7b",
    "qwen3:4b",
    "qwen3:8b",
    "qwen3:14b",
    "qwen3:30b",
    "qwen3:32b",
    "qwen3:235b",
    "deepseek-r1:8b",
    "deepseek-r1:14b",
    "deepseek-r1:32b",
    "deepseek-r1:70b",
    "llama3.1:8b",
    "llama3.1:70b",
    "gemma2:9b",
    "gemma2:27b",
    "yi:6b",
    "yi:9b",
    "yi:34b",
    "phi3:14b",
    "mistral:7b",
    "mxbai-embed-large:latest",
]

for m in models:
    r = cluster_exec('wanlida-work01', f'''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
$result = & $ollama pull {m} 2>&1
if ($LASTEXITCODE -eq 0) {{ Write-Output "AVAILABLE:{m}" }}
''', timeout=30)
    out = r.get('stdout','').strip()
    if out and "AVAILABLE" in out:
        print(out)
