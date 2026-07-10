#!/usr/bin/env python3
"""Upgrade ollama using existing installer on the node"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Stop current ollama and run installer
cmd = '''
Write-Output "=== Stopping ollama ==="
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2

Write-Output "=== Running installer ==="
$installer = "C:\\Users\\admin\\AppData\\Local\\Temp\\OllamaSetup.exe"
if (Test-Path $installer) {
    Write-Output "Installer exists: $((Get-Item $installer).Length) bytes"
    $result = Start-Process -FilePath $installer -ArgumentList "/S" -Wait -NoNewWindow -PassThru
    Write-Output "Installer exit code: $($result.ExitCode)"
} else {
    Write-Output "Installer not found at $installer"
}

Start-Sleep 3

Write-Output "=== Check new version ==="
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
if (Test-Path $ollama) {
    $ver = & $ollama --version 2>&1
    Write-Output "New version: $ver"
} else {
    $defaultPaths = @(
        "$env:LOCALAPPDATA\\Ollama\\ollama.exe",
        "$env:ProgramFiles\\Ollama\\ollama.exe"
    )
    foreach ($p in $defaultPaths) {
        if (Test-Path $p) {
            Write-Output "Found at: $p"
            $ver = & $p --version 2>&1
            Write-Output "Version: $ver"
        }
    }
}
'''
r = cluster_exec('wanlida-work01', cmd, timeout=120)
print("=== Upgrade ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
