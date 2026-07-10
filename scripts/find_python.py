#!/usr/bin/env python3
"""Find Python on wanlida-work01 and generate story"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Find Python
r1 = cluster_exec('wanlida-work01', '''
Write-Output "=== Finding Python ==="
$pythons = @()
$paths = @(
    "C:\\Python312\\python.exe",
    "C:\\Python311\\python.exe",
    "C:\\Python3\\python.exe",
    "$env:LOCALAPPDATA\\Programs\\Python\\Python312\\python.exe",
    "$env:LOCALAPPDATA\\Programs\\Python\\Python311\\python.exe",
    "$env:USERPROFILE\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
    "$env:USERPROFILE\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Output "Found: $p"
        $ver = & $p --version 2>&1
        Write-Output "  $ver"
    }
}
# Also check PATH
$pathPython = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($pathPython) {
    Write-Output "PATH python: $pathPython"
    & $pathPython --version
}
''', timeout=15)
print("=== Python search ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
