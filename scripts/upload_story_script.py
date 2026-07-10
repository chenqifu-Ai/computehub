#!/usr/bin/env python3
"""Write Python script to ECS, upload to Gallery, then run on node"""
import shutil, os

# Write the Python script
script = '''import urllib.request, json

prompt = "请用中文写一篇聊斋志异风格的短篇小说，约800字。要求：1. 文言白话结合，有聊斋的韵味 2. 包含书生、狐仙或花精等经典元素 3. 有起承转合，结尾有余韵 4. 标题自拟"

data = {
    "model": "qwen2.5:7b",
    "prompt": prompt,
    "stream": False,
    "options": {"temperature": 0.8, "num_predict": 2000}
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
print("Token数: %s | 耗时: %.2fs" % (result.get("eval_count",0), result.get("total_duration",0)/1e9))
'''

with open('/tmp/generate_story_node.py', 'w') as f:
    f.write(script)

shutil.copy('/tmp/generate_story_node.py', '/home/computehub/gallery/generate_story_node.py')
print("Script uploaded to Gallery")
