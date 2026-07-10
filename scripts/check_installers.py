#!/usr/bin/env python3
"""Upgrade ollama using existing installer on the node"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check existing installers and their versions
r = cluster_exec('wanlida-work01', '''
Write-Output "=== Existing installers ==="
$installers = @()
$paths = @("$env:TEMP", "$env:USERPROFILE\\Downloads")
foreach ($p in $paths) {
    $found = Get-ChildItem "$p\\OllamaSetup*.exe" -ErrorAction SilentlyContinue
    if ($found) { $installers += $found }
}
foreach ($f in $installers) {
    Write-Output "$($f.FullName) | $([math]::Round($f.Length/1MB,1))MB | $($f.LastWriteTime)"
}

Write-Output "=== Current ollama ==="
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
if (Test-Path $ollama) {
    $ver = & $ollama --version 2>&1
    Write-Output "Current: $ver"
}

Write-Output "=== Try running latest installer ==="
# Try the newest installer
$newest = $installers | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($newest) {
    Write-Output "Newest: $($newest.FullName) ($($newest.Length) bytes)"
    # Check if it's the latest by trying to extract version info
    $result = & $newest --version 2>&1
    Write-Output "Installer version: $result"
}
''', timeout=30)
print("=== Check ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
