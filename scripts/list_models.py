#!/usr/bin/env python3
"""List all models on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 10
    $data = $resp.Content | ConvertFrom-Json
    foreach ($m in $data.models) {
        $sizeGB = [math]::Round($m.size / 1GB, 2)
        Write-Output "$($m.name) | $($m.details.family) | $($m.details.parameter_size) | $($m.details.quantization_level) | ${sizeGB}GB"
    }
} catch { Write-Output "API error: $_" }
''', timeout=15)
print("=== 已安装模型 ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
