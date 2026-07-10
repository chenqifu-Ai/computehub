#!/usr/bin/env python3
"""Download ollama with unique filename"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\ollama_v062_$(Get-Random).zip"
Write-Output "Output: $out"

try {
    $resp = Invoke-WebRequest -Uri "http://36.250.122.43:8282/api/v1/files/ollama-windows-v0.6.2.zip" -UseBasicParsing -TimeoutSec 300 -OutFile $out
    $size = (Get-Item $out).Length
    Write-Output "Downloaded: $size bytes"
    if ($size -gt 50MB) {
        Write-Output "SIZE_OK"
        # Move to ollama dir
        Move-Item $out "$env:USERPROFILE\\ollama\\ollama_v062.zip" -Force
    } else {
        Write-Output "TOO_SMALL"
        Get-Content $out -TotalCount 5 -Encoding UTF8
    }
} catch {
    Write-Output "FAIL: $_"
}
''', timeout=600)
print("=== Download ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
