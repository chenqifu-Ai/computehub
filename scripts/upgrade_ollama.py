#!/usr/bin/env python3
"""Upgrade ollama on wanlida-work01 to latest version"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Download latest ollama
r1 = cluster_exec('wanlida-work01', '''
$url = "https://ollama.mirrors.aidc.space/ollama/ollama/releases/download/v0.6.2/OllamaSetup.exe"
$out = "$env:USERPROFILE\\ollama\\OllamaSetup_latest.exe"
Write-Output "Downloading latest ollama..."
try {
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 300
    Write-Output "Downloaded: $(Get-Item $out).Length bytes"
} catch {
    Write-Output "Download failed: $_"
    # Try official source
    $url2 = "https://ollama.com/download/OllamaSetup.exe"
    try {
        Invoke-WebRequest -Uri $url2 -OutFile $out -UseBasicParsing -TimeoutSec 300
        Write-Output "Downloaded from official: $(Get-Item $out).Length bytes"
    } catch {
        Write-Output "Official download also failed: $_"
    }
}
''', timeout=360)
print("=== Download ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
