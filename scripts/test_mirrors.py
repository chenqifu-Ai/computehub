#!/usr/bin/env python3
"""Try different Chinese ollama mirrors"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

mirrors = [
    "https://ollama.mirrors.aidc.space",
    "https://mirror.ollama.ai",
    "https://docker.1ms.run",
    "https://ghp.ci",
]

for mirror in mirrors:
    r = cluster_exec('wanlida-work01', f'''
try {{
    $resp = Invoke-WebRequest -Uri "{mirror}/v2/library/deepseek-r1/tags/list" -UseBasicParsing -TimeoutSec 10
    Write-Output "OK: {mirror} -> $($resp.StatusCode)"
    Write-Output ($resp.Content -replace '.{{200}}','...')
}} catch {{
    Write-Output "FAIL: {mirror} -> $_"
}}
''', timeout=15)
    print(f"=== {mirror} ===")
    print(r.get('stdout',''))
    print("---")
