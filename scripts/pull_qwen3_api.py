#!/usr/bin/env python3
"""Try to pull qwen3:8b via ollama API directly (bypass CLI version check)"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
# Try pulling via API directly
$body = @{
    model = "qwen3:8b"
    stream = $false
} | ConvertTo-Json

try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/pull" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 600
    Write-Output "API Status: $($resp.StatusCode)"
    Write-Output $resp.Content
} catch {
    Write-Output "API error: $_"
}
''', timeout=600)
print("=== API Pull ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
