#!/usr/bin/env python3
"""Generate 聊斋志异 story using qwen2.5:7b API"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$prompt = @"
请用中文写一篇聊斋志异风格的短篇小说，约800字。要求：
1. 文言白话结合，有聊斋的韵味
2. 包含书生、狐仙或花精等经典元素
3. 有起承转合，结尾有余韵
4. 标题自拟
"@

$body = @{
    model = "qwen2.5:7b"
    prompt = $prompt
    stream = $false
    options = @{
        temperature = 0.8
        num_predict = 2000
    }
} | ConvertTo-Json

try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 300
    $data = $resp.Content | ConvertFrom-Json
    Write-Output $data.response
    Write-Output ""
    Write-Output "---"
    Write-Output "Token数: $($data.eval_count) | 耗时: $([math]::Round($data.total_duration/1e9,2))s"
} catch {
    Write-Output "FAIL: $_"
}
''', timeout=300)
print("=== 聊斋志异小说 ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
