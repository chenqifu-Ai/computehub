#!/usr/bin/env python3
"""Upgrade ollama on wanlida-work01 via Gallery download"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Download from Gallery
r1 = cluster_exec('wanlida-work01', '''
$url = "http://36.250.122.43:8282/api/v1/files/ollama-windows-v0.6.2.zip"
$out = "$env:USERPROFILE\\ollama\\ollama_v062.zip"
Write-Output "Downloading from Gallery..."
try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($url, $out)
    $wc.Dispose()
    $size = (Get-Item $out).Length
    Write-Output "Downloaded: $size bytes"
    if ($size -gt 50MB) { Write-Output "SIZE_OK" } else { Write-Output "SIZE_TOO_SMALL" }
} catch {
    Write-Output "Download failed: $_"
}
''', timeout=600)
print("=== Download from Gallery ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
