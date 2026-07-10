#!/usr/bin/env python3
"""Check what models are available on the Chinese mirror"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check popular models on the mirror
models_to_check = [
    "qwen2.5:7b",
    "qwen2.5-coder:7b",
    "qwen2.5:14b",
    "qwen2.5:32b",
    "qwen2.5:72b",
    "deepseek-r1:8b",
    "deepseek-r1:14b",
    "deepseek-r1:32b",
    "deepseek-r1:70b",
    "deepseek-coder-v2:16b",
    "llama3.1:8b",
    "llama3.1:70b",
    "mistral:7b",
    "gemma2:9b",
    "gemma2:27b",
    "yi:6b",
    "yi:9b",
    "yi:34b",
    "phi3:14b",
    "nomic-embed-text",
    "mxbai-embed-large",
]

for m in models_to_check:
    r = cluster_exec('wanlida-work01', f'''
try {{
    $resp = Invoke-WebRequest -Uri "https://ollama.mirrors.aidc.space/v2/library/{m.Split(':')[0]}/tags/list" -UseBasicParsing -TimeoutSec 10
    $data = $resp.Content | ConvertFrom-Json
    $hasTag = $data.tags -contains "{m.Split(':')[1]}"
    if ($hasTag) {{ Write-Output "AVAILABLE: {m}" }}
}} catch {{ }}
''', timeout=12)
    out = r.get('stdout','').strip()
    if out:
        print(out)
