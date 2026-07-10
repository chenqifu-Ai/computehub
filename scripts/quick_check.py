#!/usr/bin/env python3
"""Quick check a few key models"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

models = ["qwen2.5:7b", "qwen2.5-coder:7b", "nomic-embed-text:latest"]

for m in models:
    r = cluster_exec('wanlida-work01', f'''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"
$result = & $ollama pull {m} 2>&1
if ($LASTEXITCODE -eq 0) {{
    Write-Output "✅ {m} - success"
}} else {{
    Write-Output "❌ {m} - failed"
}}
''', timeout=120)
    out = r.get('stdout','').strip()
    if out:
        print(out)
