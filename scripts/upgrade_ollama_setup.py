#!/usr/bin/env python3
"""Upgrade ollama on wanlida-work01 using existing OllamaSetup from Gallery"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Download OllamaSetup from Gallery
r1 = cluster_exec('wanlida-work01', '''
$url = "http://36.250.122.43:8282/api/v1/files/OllamaSetup_1783645797.exe"
$out = "$env:TEMP\\OllamaSetup_upgrade_$(Get-Random).exe"
Write-Output "Downloading OllamaSetup..."
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0")
    $wc.DownloadFile($url, $out)
    $wc.Dispose()
    $size = (Get-Item $out).Length
    Write-Output "Downloaded: $size bytes"
    if ($size -gt 10MB) { Write-Output "SIZE_OK" } else { Write-Output "TOO_SMALL" }
} catch {
    Write-Output "FAIL: $_"
}
''', timeout=600)
print("=== Download OllamaSetup ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
