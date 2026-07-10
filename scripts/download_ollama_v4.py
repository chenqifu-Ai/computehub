#!/usr/bin/env python3
"""Try different download methods for ollama on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Try multiple download approaches
r = cluster_exec('wanlida-work01', '''
$out = "$env:USERPROFILE\\ollama\\ollama_v062.zip"
Remove-Item $out -ErrorAction SilentlyContinue

# Method 1: Try direct file path
Write-Output "=== Method 1: Invoke-WebRequest with full URL ==="
try {
    $resp = Invoke-WebRequest -Uri "http://36.250.122.43:8282/api/v1/files/ollama-windows-v0.6.2.zip" -UseBasicParsing -TimeoutSec 300 -OutFile $out
    $size = (Get-Item $out).Length
    Write-Output "OK: $size bytes"
} catch {
    Write-Output "FAIL: $_"
    Remove-Item $out -ErrorAction SilentlyContinue
}

if (-not (Test-Path $out) -or (Get-Item $out).Length -lt 50MB) {
    # Method 2: Try with WebClient and different URL
    Write-Output "=== Method 2: WebClient ==="
    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        $wc.DownloadFile("http://36.250.122.43:8282/api/v1/files/ollama-windows-v0.6.2.zip", $out)
        $wc.Dispose()
        $size = (Get-Item $out).Length
        Write-Output "OK: $size bytes"
    } catch {
        Write-Output "FAIL: $_"
        Remove-Item $out -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $out) -or (Get-Item $out).Length -lt 50MB) {
    # Method 3: Try with curl if available
    Write-Output "=== Method 3: curl ==="
    try {
        $result = curl.exe -L -o $out "http://36.250.122.43:8282/api/v1/files/ollama-windows-v0.6.2.zip" --max-time 300 2>&1
        if (Test-Path $out) {
            $size = (Get-Item $out).Length
            Write-Output "OK: $size bytes"
        } else {
            Write-Output "FAIL: no output file"
        }
    } catch {
        Write-Output "FAIL: $_"
    }
}

if (Test-Path $out) {
    $size = (Get-Item $out).Length
    Write-Output "Final size: $size bytes"
    if ($size -gt 50MB) { Write-Output "SUCCESS" } else { Write-Output "TOO_SMALL" }
} else {
    Write-Output "NO_FILE"
}
''', timeout=600)
print("=== Download attempts ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
