#!/usr/bin/env python3
"""Clean up failed download and try alternative approach"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Clean up and try direct ollama.exe download
r = cluster_exec('wanlida-work01', '''
# Clean up
Remove-Item "$env:USERPROFILE\\ollama\\ollama_new.zip" -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\\ollama\\ollama_new" -Recurse -ErrorAction SilentlyContinue

# Try downloading just the ollama.exe from a CDN
$urls = @(
    "https://objects.githubusercontent.com/github-production-release-asset-2e65be/61893380/5b2b3e00-2e3f-11ef-8b0a-0b3c3f3b3c3e/ollama-windows-amd64.zip",
    "https://github.com/ollama/ollama/releases/download/v0.6.2/ollama-windows-amd64.zip"
)
$out = "$env:USERPROFILE\\ollama\\ollama_new.zip"

foreach ($url in $urls) {
    Write-Output "Trying: $url"
    try {
        # Use WebClient for better compatibility
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $out)
        $wc.Dispose()
        $size = (Get-Item $out).Length
        Write-Output "Downloaded: $size bytes"
        if ($size -gt 1MB) {
            Write-Output "SUCCESS"
            break
        }
    } catch {
        Write-Output "Failed: $_"
    }
}
''', timeout=600)
print("=== Download attempt ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
