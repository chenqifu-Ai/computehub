#!/usr/bin/env python3
"""Extract ollama.exe from OllamaSetup on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$installer = "C:\\Users\\admin\\AppData\\Local\\Temp\\OllamaSetup.exe"
$ollamaDir = "$env:USERPROFILE\\ollama"

Write-Output "=== Check 7z ==="
$7zPaths = @(
    "C:\\Program Files\\7-Zip\\7z.exe",
    "C:\\Program Files (x86)\\7-Zip\\7z.exe",
    "$env:USERPROFILE\\scoop\\apps\\7zip\\current\\7z.exe"
)
$7z = $null
foreach ($p in $7zPaths) {
    if (Test-Path $p) { $7z = $p; break }
}
if (-not $7z) {
    # Check if 7z is in PATH
    $7z = (Get-Command 7z -ErrorAction SilentlyContinue).Source
}
if ($7z) {
    Write-Output "Found 7z: $7z"
    # Try to extract ollama.exe from the installer
    $outDir = "$env:TEMP\\ollama_extract_$(Get-Random)"
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    $result = & $7z x $installer -o"$outDir" -y ollama.exe 2>&1
    Write-Output "Extract result: $result"
    $found = Get-ChildItem -Path $outDir -Recurse -Filter "ollama.exe" -ErrorAction SilentlyContinue
    if ($found) {
        Write-Output "Found ollama.exe at: $($found.FullName)"
        Write-Output "Size: $($found.Length) bytes"
    } else {
        Write-Output "ollama.exe not found in installer"
        Get-ChildItem $outDir -Recurse | Select-Object Name,Length | Format-Table -AutoSize
    }
} else {
    Write-Output "7z not found"
}
''', timeout=60)
print("=== Extract ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
