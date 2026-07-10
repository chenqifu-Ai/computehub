#!/usr/bin/env python3
"""Download latest ollama.exe directly from ollama.com on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\ollama_exe_$(Get-Random).exe"

# Try multiple download methods
Write-Output "=== Method 1: Invoke-WebRequest ==="
try {
    $resp = Invoke-WebRequest -Uri "https://ollama.com/download/ollama-windows-amd64.exe" -UseBasicParsing -TimeoutSec 300 -OutFile $out
    $size = (Get-Item $out).Length
    Write-Output "Downloaded: $size bytes"
    if ($size -gt 10MB) { Write-Output "SIZE_OK" }
} catch {
    Write-Output "FAIL: $_"
    Remove-Item $out -ErrorAction SilentlyContinue
}

if (-not (Test-Path $out) -or (Get-Item $out).Length -lt 1MB) {
    Write-Output "=== Method 2: WebClient ==="
    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        $wc.DownloadFile("https://ollama.com/download/ollama-windows-amd64.exe", $out)
        $wc.Dispose()
        $size = (Get-Item $out).Length
        Write-Output "Downloaded: $size bytes"
        if ($size -gt 10MB) { Write-Output "SIZE_OK" }
    } catch {
        Write-Output "FAIL: $_"
        Remove-Item $out -ErrorAction SilentlyContinue
    }
}

if (Test-Path $out) {
    $size = (Get-Item $out).Length
    Write-Output "Final: $size bytes"
    if ($size -gt 10MB) { Write-Output "SUCCESS" }
}
''', timeout=600)
print("=== Download ollama.exe ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
