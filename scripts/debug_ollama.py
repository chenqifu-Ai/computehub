#!/usr/bin/env python3
"""Debug ollama startup failure on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check log
r1 = cluster_exec('wanlida-work01', '''
$log = "$env:USERPROFILE\\ollama\\ollama.log"
$err = "$env:USERPROFILE\\ollama\\ollama.log.err"
if (Test-Path $log) { Write-Output "=== stdout log ==="; Get-Content $log }
if (Test-Path $err) { Write-Output "=== stderr log ==="; Get-Content $err }
Write-Output "=== dir ==="
Get-ChildItem "$env:USERPROFILE\\ollama" | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
''', timeout=15)
print("=== Debug ===")
print(r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))

# Try running ollama serve directly and capture output
r2 = cluster_exec('wanlida-work01', '''
$ollama = "$env:USERPROFILE\\ollama\\ollama.exe"
$result = & $ollama serve 2>&1
Start-Sleep 2
Write-Output "serve output: $result"
# Check if process started
$proc = Get-Process ollama -ErrorAction SilentlyContinue
if ($proc) { Write-Output "process running: PID=$($proc.Id)" } else { Write-Output "process NOT running" }
''', timeout=20)
print("\n=== Direct serve ===")
print(r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))
