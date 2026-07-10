#!/usr/bin/env python3
"""Generate story and save to file on node, then read back"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write Python script to node via base64
import base64
py_code = '''import urllib.request, json, sys
prompt = "请用中文写一篇聊斋志异风格的短篇小说，约800字。要求：1. 文言白话结合，有聊斋的韵味 2. 包含书生、狐仙或花精等经典元素 3. 有起承转合，结尾有余韵 4. 标题自拟"
data = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False, "options": {"temperature": 0.8, "num_predict": 2000}}
req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=300)
result = json.loads(resp.read().decode("utf-8"))
story = result.get("response", "")
tokens = result.get("eval_count", 0)
duration = result.get("total_duration", 0) / 1e9
# Write to file
with open("C:\\\\Users\\\\admin\\\\ollama\\\\story_output.txt", "w", encoding="utf-8") as f:
    f.write(story)
    f.write("\\n---\\n")
    f.write(f"Token数: {tokens} | 耗时: {duration:.2f}s")
print("SAVED_TO_FILE")
'''

b64 = base64.b64encode(py_code.encode()).decode()

r1 = cluster_exec('wanlida-work01', f'''
$b64 = "{b64}"
$bytes = [Convert]::FromBase64String($b64)
$out = "$env:TEMP\\gen_story_save_$(Get-Random).py"
[System.IO.File]::WriteAllBytes($out, $bytes)
$python = "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
& $python $out 2>&1
''', timeout=300)
print("=== Generate ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))

# Read the file back
r2 = cluster_exec('wanlida-work01', 'Get-Content "$env:USERPROFILE\\ollama\\story_output.txt" -Encoding UTF8', timeout=15)
print("\n=== 聊斋志异小说 ===")
print(r2.get('stdout',''))
print("exit_code:", r2.get('exit_code',''))
