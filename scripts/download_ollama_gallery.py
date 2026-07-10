#!/usr/bin/env python3
"""Download ollama from Gallery using curl on the node"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\ollama_gallery_$(Get-Random).exe"

Write-Output "=== Download from Gallery with curl ==="
try {
    $result = curl.exe -L -o $out "http://36.250.122.43:8282/api/v1/files/OllamaSetup_1783645797.exe" --max-time 600 2>&1
    Write-Output "curl result: $result"
    if (Test-Path $out) {
        $size = (Get-Item $out).Length
        Write-Output "Downloaded: $size bytes"
        if ($size -gt 10MB) { Write-Output "SUCCESS" }
    }
} catch {
    Write-Output "FAIL: $_"
}

if (Test-Path $out) {
    $size = (Get-Item $out).Length
    Write-Output "Final: $size bytes"
    if ($size -gt 10MB) { Write-Output "SIZE_OK" }
}
''', timeout=600)
print("=== Gallery download ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
