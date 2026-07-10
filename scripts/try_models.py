#!/usr/bin/env python3
"""Try pulling a few popular models to see what's available"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Just check what's already on the mirror by trying to pull manifest
models_to_try = [
    "qwen2.5:7b",
    "qwen2.5-coder:7b",
    "qwen2.5:14b",
    "deepseek-r1:14b",
    "gemma2:9b",
    "llama3.1:8b",
    "yi:6b",
    "nomic-embed-text:latest",
]

for m in models_to_try:
    r = cluster_exec('wanlida-work01', f'''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
# Just check if manifest exists (quick check, no download)
$result = & $ollama pull {m} 2>&1
if ($LASTEXITCODE -eq 0 -or $result -match "already") {{
    Write-Output "✅ {m} - available"
}} else {{
    Write-Output "❌ {m} - not available"
}}
''', timeout=30)
    out = r.get('stdout','').strip()
    if out:
        print(out)
