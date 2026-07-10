#!/usr/bin/env python3
"""Debug deepseek-r1:7b pull failure and try alternative"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check ollama log
r1 = cluster_exec('wanlida-work01', '''
$log = "$env:USERPROFILE\\ollama\\ollama.log"
$err = "$env:USERPROFILE\\ollama\\ollama.log.err"
if (Test-Path $log) { Write-Output "=== log ==="; Get-Content $log -Tail 20 }
if (Test-Path $err) { Write-Output "=== err ==="; Get-Content $err -Tail 20 }
''', timeout=10)
print("=== Log ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))

# Check if mirror has deepseek-r1
r2 = cluster_exec('wanlida-work01', '''
try {
    $resp = Invoke-WebRequest -Uri "https://ollama.mirrors.aidc.space/v2/library/deepseek-r1/tags/list" -UseBasicParsing -TimeoutSec 10
    Write-Output "mirror tags: $($resp.StatusCode)"
    Write-Output $resp.Content
} catch { Write-Output "mirror check: $_" }
''', timeout=15)
print("\n=== Mirror Tags ===")
print(r2.get('stdout',''))
print("exit_code:", r2.get('exit_code',''))
