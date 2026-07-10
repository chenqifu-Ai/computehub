#!/usr/bin/env python3
"""Generate 聊斋 story - write script to file on ECS, upload to Gallery, run on node"""
import sys, base64, os
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write the Python script to a temp file on ECS
script = '''import urllib.request, json
prompt = "\u8bf7\u7528\u4e2d\u6587\u5199\u4e00\u7bc7\u804a\u9f50\u5fd7\u5f02\u98ce\u683c\u7684\u77ed\u7bc7\u5c0f\u8bf4\uff0c\u7ea6800\u5b57\u3002\u8981\u6c42\uff1a1. \u6587\u8a00\u767d\u8bdd\u7ed3\u5408\uff0c\u6709\u804a\u9f50\u7684\u97f5\u5473 2. \u5305\u542b\u4e66\u751f\u3001\u72d0\u4ed9\u6216\u82b1\u7cbe\u7b49\u7ecf\u5178\u5143\u7d20 3. \u6709\u8d77\u627f\u8f6c\u5408\uff0c\u7ed3\u5c3e\u6709\u4f59\u97f5 4. \u6807\u9898\u81ea\u62df"
data = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False, "options": {"temperature": 0.8, "num_predict": 2000}}
req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=300)
result = json.loads(resp.read().decode("utf-8"))
print(result.get("response", ""))
print("---")
print("Token count: %s | Time: %.2fs" % (result.get("eval_count",0), result.get("total_duration",0)/1e9))
'''

with open('/tmp/gen_story_node.py', 'w') as f:
    f.write(script)

# Upload to Gallery
import shutil
shutil.copy('/tmp/gen_story_node.py', '/home/computehub/gallery/gen_story_node.py')
print("Script uploaded to Gallery")

# Now download and run on node
r = cluster_exec('wanlida-work01', '''
$url = "http://36.250.122.43:8282/api/v1/files/gen_story_node.py"
$out = "$env:TEMP\\gen_story_$(Get-Random).py"
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0")
    $wc.DownloadFile($url, $out)
    $wc.Dispose()
    Write-Output "Downloaded: $((Get-Item $out).Length) bytes"
    python3 $out 2>&1
} catch {
    Write-Output "FAIL: $_"
}
''', timeout=300)
print("=== 聊斋志异小说 ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
