#!/usr/bin/env python3
"""Check what the node can actually download from"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
Write-Output "=== DNS test ==="
try {
    $ips = [System.Net.Dns]::GetHostAddresses("ollama.mirrors.aidc.space")
    Write-Output "mirror DNS: $($ips.IPAddressToString -join ',')"
} catch { Write-Output "mirror DNS FAIL: $_" }

try {
    $ips = [System.Net.Dns]::GetHostAddresses("ollama.com")
    Write-Output "ollama.com DNS: $($ips.IPAddressToString -join ',')"
} catch { Write-Output "ollama.com DNS FAIL: $_" }

try {
    $ips = [System.Net.Dns]::GetHostAddresses("github.com")
    Write-Output "github.com DNS: $($ips.IPAddressToString -join ',')"
} catch { Write-Output "github.com DNS FAIL: $_" }

Write-Output "=== Test downloads ==="
$tests = @(
    @("ollama.com", "https://ollama.com"),
    @("github", "https://github.com"),
    @("baidu", "https://www.baidu.com")
)
foreach ($t in $tests) {
    try {
        $resp = Invoke-WebRequest -Uri $t[1] -UseBasicParsing -TimeoutSec 10 -Method Head
        Write-Output "$($t[0]): $($resp.StatusCode)"
    } catch {
        Write-Output "$($t[0]): FAIL - $_"
    }
}
''', timeout=30)
print("=== Network check ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
