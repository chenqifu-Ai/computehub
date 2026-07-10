#!/usr/bin/env python3
"""Quick check what's on the mirror"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Check a batch of popular models
r = cluster_exec('wanlida-work01', '''
$mirror = "https://ollama.mirrors.aidc.space"
$models = @(
    @("qwen2.5","7b"),
    @("qwen2.5","14b"),
    @("qwen2.5","32b"),
    @("qwen2.5","72b"),
    @("qwen2.5-coder","7b"),
    @("qwen2.5-coder","14b"),
    @("qwen2.5-coder","32b"),
    @("deepseek-r1","8b"),
    @("deepseek-r1","14b"),
    @("deepseek-r1","32b"),
    @("deepseek-r1","70b"),
    @("llama3.1","8b"),
    @("llama3.1","70b"),
    @("gemma2","9b"),
    @("gemma2","27b"),
    @("yi","6b"),
    @("yi","9b"),
    @("yi","34b"),
    @("phi3","14b"),
    @("mistral","7b"),
    @("nomic-embed-text","latest"),
    @("mxbai-embed-large","latest")
)
foreach ($m in $models) {
    $name = $m[0]; $tag = $m[1]
    try {
        $resp = Invoke-WebRequest -Uri "$mirror/v2/library/$name/tags/list" -UseBasicParsing -TimeoutSec 8 -ErrorAction Stop
        $data = $resp.Content | ConvertFrom-Json
        if ($data.tags -contains $tag) { Write-Output "✅ $name`:$tag" }
    } catch { }
}
''', timeout=180)
print("=== 镜像可用模型 ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
