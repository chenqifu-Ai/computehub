#!/usr/bin/env python3
"""Install ollama on wanlida-work01 (Windows, no admin)"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Step 1: Find the existing installer
r1 = cluster_exec('wanlida-work01', '''
$files = @()
$paths = @("$env:TEMP", "$env:USERPROFILE\\Downloads")
foreach ($p in $paths) {
    $found = Get-ChildItem "$p\\ollama*.exe" -ErrorAction SilentlyContinue
    if ($found) { $files += $found.FullName }
}
$files | ForEach-Object { Write-Output $_ }
if ($files.Count -eq 0) { Write-Output "no_installer_found" }
''', timeout=10)
print("=== Existing Installers ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))
