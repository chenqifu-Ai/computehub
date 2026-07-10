#!/usr/bin/env python3
"""Generate story and save to file on node, then read back"""
import sys, base64
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

py_code = (
    'import urllib.request, json\n'
    'prompt = "\u8bf7\u7528\u4e2d\u6587\u5199\u4e00\u7bc7\u804a\u9f50\u5fd7\u5f02\u98ce\u683c\u7684\u77ed\u7bc7\u5c0f\u8bf4\uff0c\u7ea6800\u5b57\u3002\u8981\u6c42\uff1a1. \u6587\u8a00\u767d\u8bdd\u7ed3\u5408\uff0c\u6709\u804a\u9f50\u7684\u97f5\u5473 2. \u5305\u542b\u4e66\u751f\u3001\u72d0\u4ed9\u6216\u82b1\u7cbe\u7b49\u7ecf\u5178\u5143\u7d20 3. \u6709\u8d77\u627f\u8f6c\u5408\uff0c\u7ed3\u5c3e\u6709\u4f59\u97f5 4. \u6807\u9898\u81ea\u62df"\n'
    'data = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False, "options": {"temperature": 0.8, "num_predict": 2000}}\n'
    'req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})\n'
    'resp = urllib.request.urlopen(req, timeout=300)\n'
    'result = json.loads(resp.read().decode("utf-8"))\n'
    'story = result.get("response", "")\n'
    'tokens = result.get("eval_count", 0)\n'
    'duration = result.get("total_duration", 0) / 1e9\n'
    'with open("C:\\\\Users\\\\admin\\\\ollama\\\\story_output.txt", "w", encoding="utf-8") as f:\n'
    '    f.write(story)\n'
    '    f.write("\\n---\\n")\n'
    '    f.write("Token count: " + str(tokens) + " | Time: " + str(round(duration, 2)) + "s")\n'
    'print("SAVED")\n'
)

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
