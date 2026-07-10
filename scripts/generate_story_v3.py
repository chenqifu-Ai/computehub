#!/usr/bin/env python3
"""Generate 聊斋志异 story - write prompt to file first to avoid encoding issues"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Write prompt to file on node
r1 = cluster_exec('wanlida-work01', '''
$prompt = @"
请用中文写一篇聊斋志异风格的短篇小说，约800字。要求：
1. 文言白话结合，有聊斋的韵味
2. 包含书生、狐仙或花精等经典元素
3. 有起承转合，结尾有余韵
4. 标题自拟
"@

$promptFile = "$env:TEMP\\story_prompt.txt"
# Use UTF8NoBOM encoding
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($promptFile, $prompt, $utf8)
Write-Output "Prompt written to $promptFile"
''', timeout=15)
print(r1.get('stdout',''))

# Step 2: Read prompt from file and call API
r2 = cluster_exec('wanlida-work01', '''
$promptFile = "$env:TEMP\\story_prompt.txt"
$prompt = [System.IO.File]::ReadAllText($promptFile)

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
print(r2.get('stdout',''))
print("exit_code:", r2.get('exit_code',''))
