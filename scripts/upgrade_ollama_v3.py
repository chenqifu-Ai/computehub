#!/usr/bin/env python3
"""Clean up and download ollama v0.6.2 from Gallery"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
# Clean up any partial downloads
Remove-Item "$env:USERPROFILE\\ollama\\ollama_v062.zip" -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\\ollama\\ollama_new.zip" -ErrorAction SilentlyContinue
Start-Sleep 1

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
print("=== Download ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
