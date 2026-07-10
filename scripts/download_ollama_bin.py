#!/usr/bin/env python3
"""Download latest ollama binary for Windows"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Try downloading the portable ollama binary from GitHub via mirror
r = cluster_exec('wanlida-work01', '''
# Try multiple sources for the ollama windows binary
$urls = @(
    "https://github.com/ollama/ollama/releases/download/v0.6.2/ollama-windows-amd64.zip",
    "https://ghp.ci/https://github.com/ollama/ollama/releases/download/v0.6.2/ollama-windows-amd64.zip",
    "https://ghproxy.net/https://github.com/ollama/ollama/releases/download/v0.6.2/ollama-windows-amd64.zip"
)
$out = "$env:USERPROFILE\\ollama\\ollama_new.zip"
$success = $false
foreach ($url in $urls) {
    Write-Output "Trying: $url"
    try {
        Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 120
        if ((Get-Item $out).Length -gt 1MB) {
            Write-Output "Downloaded: $((Get-Item $out).Length) bytes"
            $success = $true
            break
        }
    } catch {
        Write-Output "Failed: $_"
    }
}
if (-not $success) { Write-Output "ALL_FAILED" }
''', timeout=600)
print("=== Download binary ===")
print(r.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
