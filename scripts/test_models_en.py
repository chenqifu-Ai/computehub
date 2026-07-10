#!/usr/bin/env python3
"""Test both models with English prompts to avoid encoding issues"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

models = ["deepseek-r1:7b", "qwen2.5:7b"]

for model in models:
    # Test: Math reasoning (English)
    r = cluster_exec('wanlida-work01', f'''
try {{
    $body = @{{
        model="{model}"
        prompt="Solve step by step: A pool has two pipes. Pipe A fills the pool in 6 hours alone. Pipe B fills the pool in 8 hours alone. If both pipes are opened together, how many hours will it take to fill the pool?"
        stream=$false
    }} | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 120
    $data = $resp.Content | ConvertFrom-Json
    Write-Output "=== {model} 数学推理(英文) ==="
    Write-Output "回答: $($data.response)"
    Write-Output "耗时: $([math]::Round($data.total_duration/1e9,2))s"
    Write-Output "Token数: $($data.eval_count)"
    Write-Output "速度: $([math]::Round($data.eval_count / ($data.eval_duration/1e9),1)) tokens/s"
}} catch {{ Write-Output "FAIL: $_" }}
''', timeout=180)
    print(r.get('stdout',''))
    print("---")
