#!/usr/bin/env python3
"""Download latest ollama from Chinese mirror on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\ollama_latest_$(Get-Random).exe"
$mirrors = @(
    "https://ollama.mirrors.aidc.space/ollama/ollama/releases/download/v0.6.2/OllamaSetup.exe",
    "https://ollama.mirrors.aidc.space/ollama/ollama/releases/download/v0.5.13/OllamaSetup.exe"
)

foreach ($url in $mirrors) {
    Write-Output "Trying: $url"
    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        $wc.DownloadFile($url, $out)
        $wc.Dispose()
        $size = (Get-Item $out).Length
        Write-Output "Downloaded: $size bytes"
        if ($size -gt 10MB) {
            Write-Output "SUCCESS"
            break
        }
    } catch {
        Write-Output "FAIL: $_"
        Remove-Item $out -ErrorAction SilentlyContinue
    }
}

if (Test-Path $out) {
    $size = (Get-Item $out).Length
    Write-Output "Final: $size bytes"
    if ($size -gt 10MB) { Write-Output "SIZE_OK" }
}
''', timeout=600)
print("=== Download ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
