#!/usr/bin/env python3
"""Try to extract ollama.exe from existing OllamaSetup on the node"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$installer = "C:\\Users\\admin\\AppData\\Local\\Temp\\OllamaSetup.exe"
$ollamaDir = "$env:USERPROFILE\\ollama"

Write-Output "=== Check installer ==="
Write-Output "Size: $((Get-Item $installer).Length) bytes"

# Try to run the installer with /S (silent) - might work without admin
Write-Output "=== Try silent install ==="
try {
    $proc = Start-Process -FilePath $installer -ArgumentList "/S /D=$ollamaDir" -Wait -NoNewWindow -PassThru
    Write-Output "Exit code: $($proc.ExitCode)"
} catch {
    Write-Output "FAIL: $_"
}

Start-Sleep 3

Write-Output "=== Check version ==="
$ollama = "$ollamaDir\\ollama.exe"
if (Test-Path $ollama) {
    $ver = & $ollama --version 2>&1
    Write-Output "Version: $ver"
} else {
    Write-Output "ollama.exe not found at $ollamaDir"
    # Check if installed elsewhere
    $paths = @("$env:LOCALAPPDATA\\Ollama\\ollama.exe", "$env:ProgramFiles\\Ollama\\ollama.exe")
    foreach ($p in $paths) {
        if (Test-Path $p) {
            Write-Output "Found at: $p"
            $ver = & $p --version 2>&1
            Write-Output "Version: $ver"
        }
    }
}
''', timeout=120)
print("=== Install attempt ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
