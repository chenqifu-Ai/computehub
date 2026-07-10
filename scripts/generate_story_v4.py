#!/usr/bin/env python3
"""Generate 聊斋志异 story using Python on the node to avoid encoding issues"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write a Python script to the node that calls the ollama API
r1 = cluster_exec('wanlida-work01', '''
$pyCode = @'
import urllib.request
import json

prompt = """请用中文写一篇聊斋志异风格的短篇小说，约800字。要求：
1. 文言白话结合，有聊斋的韵味
2. 包含书生、狐仙或花精等经典元素
3. 有起承转合，结尾有余韵
4. 标题自拟"""

data = {
    "model": "qwen2.5:7b",
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0.8,
        "num_predict": 2000
    }
}

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

resp = urllib.request.urlopen(req, timeout=300)
result = json.loads(resp.read().decode("utf-8"))
print(result.get("response", ""))
print("---")
print(f"Token数: {result.get('eval_count',0)} | 耗时: {result.get('total_duration',0)/1e9:.2f}s")
'@

$pyFile = "$env:TEMP\\generate_story.py"
Set-Content -Path $pyFile -Value $pyCode -Encoding UTF8
Write-Output "Script written"
''', timeout=15)
print(r1.get('stdout',''))

# Run the Python script
r2 = cluster_exec('wanlida-work01', 'python3 "$env:TEMP\\generate_story.py" 2>&1', timeout=300)
print("=== 聊斋志异小说 ===")
print(r2.get('stdout',''))
print("exit_code:", r2.get('exit_code',''))
