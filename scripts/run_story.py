#!/usr/bin/env python3
"""Download and run story generation script on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Download script from Gallery and run
r = cluster_exec('wanlida-work01', '''
$url = "http://36.250.122.43:8282/api/v1/files/generate_story_node.py"
$out = "$env:TEMP\\gen_story_$(Get-Random).py"
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0")
    $wc.DownloadFile($url, $out)
    $wc.Dispose()
    Write-Output "Downloaded: $((Get-Item $out).Length) bytes"
} catch {
    Write-Output "Download FAIL: $_"
    # Write directly
    $code = @'
import urllib.request, json
prompt = "请用中文写一篇聊斋志异风格的短篇小说，约800字。要求：1. 文言白话结合，有聊斋的韵味 2. 包含书生、狐仙或花精等经典元素 3. 有起承转合，结尾有余韵 4. 标题自拟"
data = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False, "options": {"temperature": 0.8, "num_predict": 2000}}
req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=300)
result = json.loads(resp.read().decode("utf-8"))
print(result.get("response", ""))
print("---")
print("Token数: %s | 耗时: %.2fs" % (result.get("eval_count",0), result.get("total_duration",0)/1e9))
'@
    $out = "$env:TEMP\\gen_story_$(Get-Random).py"
    Set-Content -Path $out -Value $code -Encoding UTF8
    Write-Output "Script written directly"
}

Write-Output "=== Running ==="
python3 $out 2>&1
''', timeout=300)
print("=== 聊斋志异小说 ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
