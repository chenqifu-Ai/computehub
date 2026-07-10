#!/usr/bin/env python3
"""Check ollama installation status on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check common install locations
r1 = cluster_exec('wanlida-work01', '''
$paths = @(
    "$env:LOCALAPPDATA\\Ollama",
    "$env:ProgramFiles\\Ollama",
    "${env:ProgramFiles(x86)}\\Ollama",
    "$env:USERPROFILE\\AppData\\Local\\Ollama",
    "$env:USERPROFILE\\ollama"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Output "FOUND: $p"
        Get-ChildItem $p -ErrorAction SilentlyContinue | Select-Object Name,Length | Format-Table -AutoSize
    }
}
Write-Output "---"
# Check if ollama.exe is anywhere
$exe = Get-ChildItem -Path C:\ -Recurse -Filter "ollama.exe" -ErrorAction SilentlyContinue -Depth 3
if ($exe) { Write-Output "ollama.exe at: $($exe.FullName)" } else { Write-Output "ollama.exe not found in C:\\ depth 3" }
''', timeout=30)
print("=== Install Locations ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))
