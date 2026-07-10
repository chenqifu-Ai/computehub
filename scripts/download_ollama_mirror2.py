#!/usr/bin/env python3
"""Download ollama binary via the mirror that works for model pulls"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\ollama_new_$(Get-Random).exe"

# The mirror that works for model pulls
$env:OLLAMA_BASE_URL = "https://ollama.mirrors.aidc.space"

# Try to download ollama binary from the mirror
# First check if the mirror has the binary
Write-Output "=== Check mirror connectivity ==="
try {
    $resp = Invoke-WebRequest -Uri "https://ollama.mirrors.aidc.space" -UseBasicParsing -TimeoutSec 10
    Write-Output "Mirror root: $($resp.StatusCode)"
} catch {
    Write-Output "Mirror root FAIL: $_"
}

# Try downloading from the mirror's GitHub proxy
Write-Output "=== Download ollama.exe from mirror ==="
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0")
    $wc.DownloadFile("https://ollama.mirrors.aidc.space/ollama/ollama/releases/download/v0.6.2/ollama-windows-amd64.exe", $out)
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
print("=== Download from mirror ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
