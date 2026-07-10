#!/usr/bin/env python3
"""Download latest ollama from ollama.com via the node's internet"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\OllamaSetup_latest_$(Get-Random).exe"

Write-Output "=== Flush DNS ==="
ipconfig /flushdns 2>&1 | Out-Null
Start-Sleep 2

Write-Output "=== Download from ollama.com ==="
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    $wc.DownloadFile("https://ollama.com/download/OllamaSetup.exe", $out)
    $wc.Dispose()
    $size = (Get-Item $out).Length
    Write-Output "Downloaded: $size bytes"
    if ($size -gt 10MB) { Write-Output "SUCCESS" }
} catch {
    Write-Output "FAIL: $_"
    Remove-Item $out -ErrorAction SilentlyContinue
}

if (Test-Path $out) {
    $size = (Get-Item $out).Length
    Write-Output "Final: $size bytes"
    if ($size -gt 10MB) { Write-Output "SIZE_OK" }
}
''', timeout=600)
print("=== Download OllamaSetup ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
