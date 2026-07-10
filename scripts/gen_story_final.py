#!/usr/bin/env python3
"""Generate 聊斋 story - write Python script to node and run"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write Python script to node using base64 to avoid encoding issues
import base64

py_code = '''import urllib.request, json
prompt = "\u8bf7\u7528\u4e2d\u6587\u5199\u4e00\u7bc7\u804a\u9f50\u5fd7\u5f02\u98ce\u683c\u7684\u77ed\u7bc7\u5c0f\u8bf4\uff0c\u7ea6800\u5b57\u3002\u8981\u6c42\uff1a1. \u6587\u8a00\u767d\u8bdd\u7ed3\u5408\uff0c\u6709\u804a\u9f50\u7684\u97f5\u5473 2. \u5305\u542b\u4e66\u751f\u3001\u72d0\u4ed9\u6216\u82b1\u7cbe\u7b49\u7ecf\u5178\u5143\u7d20 3. \u6709\u8d77\u627f\u8f6c\u5408\uff0c\u7ed3\u5c3e\u6709\u4f59\u97f5 4. \u6807\u9898\u81ea\u62df"
data = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False, "options": {"temperature": 0.8, "num_predict": 2000}}
req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=300)
result = json.loads(resp.read().decode("utf-8"))
print(result.get("response", ""))
print("---")
print("Token\u6570: %s | \u8017\u65f6: %.2fs" % (result.get("eval_count",0), result.get("total_duration",0)/1e9))
'''

b64 = base64.b64encode(py_code.encode()).decode()

r = cluster_exec('wanlida-work01', f'''
$b64 = "{b64}"
$bytes = [Convert]::FromBase64String($b64)
$out = "$env:TEMP\\gen_story_$(Get-Random).py"
[System.IO.File]::WriteAllBytes($out, $bytes)
Write-Output "Script written: $((Get-Item $out).Length) bytes"
python3 $out 2>&1
''', timeout=300)
print("=== 聊斋志异小说 ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
