#!/usr/bin/env python3
"""Try to download ollama binary from ollama.com CDN"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$out = "$env:TEMP\\ollama_bin_$(Get-Random).exe"

# Try different download URLs
$urls = @(
    "https://ollama.com/download/ollama-windows-amd64.exe",
    "https://ollama.com/download/OllamaSetup.exe",
    "https://objects.githubusercontent.com/github-production-release-asset-2e65be/61893380/5b2b3e00-2e3f-11ef-8b0a-0b3c3f3b3c3e/ollama-windows-amd64.zip"
)

foreach ($url in $urls) {
    Write-Output "Trying: $url"
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10 -Method Head
        Write-Output "  HEAD: $($resp.StatusCode) $($resp.ContentLength) bytes"
        if ($resp.ContentLength -gt 10MB) {
            Write-Output "  Downloading..."
            $wc = New-Object System.Net.WebClient
            $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            $wc.DownloadFile($url, $out)
            $wc.Dispose()
            $size = (Get-Item $out).Length
            Write-Output "  Downloaded: $size bytes"
            if ($size -gt 10MB) { Write-Output "  SUCCESS"; break }
        }
    } catch {
        Write-Output "  FAIL: $_"
        Remove-Item $out -ErrorAction SilentlyContinue
    }
}

if (Test-Path $out) {
    $size = (Get-Item $out).Length
    Write-Output "Final: $size bytes"
    if ($size -gt 10MB) { Write-Output "SIZE_OK" }
} else {
    Write-Output "NO_FILE"
}
''', timeout=600)
print("=== Download attempts ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
