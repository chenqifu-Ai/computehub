#!/usr/bin/env python3
"""Generate 聊斋志异 story using qwen2.5:7b on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write prompt to a file on the node to avoid encoding issues
r1 = cluster_exec('wanlida-work01', '''
$prompt = @"
请用中文写一篇聊斋志异风格的短篇小说，约800字。要求：
1. 文言白话结合，有聊斋的韵味
2. 包含书生、狐仙/花精等经典元素
3. 有起承转合，结尾有余韵
4. 标题自拟
"@

$promptFile = "$env:TEMP\\story_prompt.txt"
Set-Content -Path $promptFile -Value $prompt -Encoding UTF8
Write-Output "Prompt written"
''', timeout=15)
print(r1.get('stdout',''))

# Now use the model with the prompt from file
r2 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$promptFile = "$env:TEMP\\story_prompt.txt"
$prompt = Get-Content $promptFile -Raw -Encoding UTF8

# Use ollama run with the prompt
$result = & $ollama run qwen2.5:7b $prompt 2>&1
Write-Output $result
''', timeout=300)
print("=== 小说 ===")
print(r2.get('stdout',''))
print("exit_code:", r2.get('exit_code',''))
