#!/usr/bin/env python3
"""Check wanlida-work01 pre-install status for ollama"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# 1. Admin check + disk space + arch
r1 = cluster_exec('wanlida-work01', '''
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Output "isAdmin: $isAdmin"
$drives = Get-PSDrive C | Select-Object Used,Free
Write-Output "C_drive_GB: $([math]::Round($drives.Free/1GB,1)) free / $([math]::Round(($drives.Used+$drives.Free)/1GB,1)) total"
Write-Output "arch: $env:PROCESSOR_ARCHITECTURE"
''', timeout=15)
print("=== Pre-install Check ===")
print("stdout:", r1.get('stdout',''))
print("stderr:", r1.get('stderr',''))
print("exit_code:", r1.get('exit_code',''))

# 2. Check GPU info
r2 = cluster_exec('wanlida-work01', 'Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion', timeout=15)
print("\n=== GPU Info ===")
print("stdout:", r2.get('stdout',''))
print("stderr:", r2.get('stderr',''))
print("exit_code:", r2.get('exit_code',''))

# 3. Check if ollama installer already exists
r3 = cluster_exec('wanlida-work01', 'Test-Path "$env:TEMP\\ollama*.exe"; Test-Path "$env:USERPROFILE\\Downloads\\ollama*.exe"; Write-Output "done"', timeout=10)
print("\n=== Existing Installers ===")
print("stdout:", r3.get('stdout',''))
print("stderr:", r3.get('stderr',''))
print("exit_code:", r3.get('exit_code',''))
