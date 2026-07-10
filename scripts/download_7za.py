#!/usr/bin/env python3
"""Use 7za from Gallery to extract OllamaSetup on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Download 7za.exe from Gallery
r1 = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\7za_$(Get-Random).exe"
$url = "http://36.250.122.43:8282/api/v1/files/7za.exe"
Write-Output "Downloading 7za..."
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0")
    $wc.DownloadFile($url, $out)
    $wc.Dispose()
    $size = (Get-Item $out).Length
    Write-Output "Downloaded: $size bytes"
    if ($size -gt 100KB) { Write-Output "SIZE_OK" }
} catch {
    Write-Output "FAIL: $_"
}
''', timeout=120)
print("=== Download 7za ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
