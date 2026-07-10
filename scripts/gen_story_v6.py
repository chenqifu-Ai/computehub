#!/usr/bin/env python3
"""Generate 聊斋 story using full Python path"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$url = "http://36.250.122.43:8282/api/v1/files/gen_story_node.py"
$out = "$env:TEMP\\gen_story_$(Get-Random).py"
$python = "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"

try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0")
    $wc.DownloadFile($url, $out)
    $wc.Dispose()
    Write-Output "Downloaded: $((Get-Item $out).Length) bytes"
    & $python $out 2>&1
} catch {
    Write-Output "FAIL: $_"
}
''', timeout=300)
print("=== 聊斋志异小说 ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
