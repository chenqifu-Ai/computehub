# Ollama 模型下载脚本
# 用法：.\pull_model.ps1 ministral-3:14b

$MODEL = $args[0]
if (-not $MODEL) { $MODEL = "ministral-3:14b" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📥 Ollama 模型下载" -ForegroundColor Cyan
Write-Host "   模型：$MODEL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$LAST_SIZE = 0
$LAST_TIME = Get-Date

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/pull" -Method POST -Body "{\"name\":\"$MODEL\"}" -ContentType "application/json" -TimeoutSec 300
    $lines = $response.Content -split "`n"
    
    foreach ($line in $lines) {
        if ($line.Trim()) {
            try {
                $data = $line | ConvertFrom-Json
                
                if ($data.status -eq "success") {
                    Write-Host "`n✅ 下载完成!" -ForegroundColor Green
                    Write-Host "   模型：$MODEL" -ForegroundColor Green
                    break
                }
                
                if ($data.completed -and $data.total) {
                    $percent = [math]::Round(($data.completed / $data.total) * 100, 1)
                    $completed_gb = [math]::Round($data.completed / 1GB, 2)
                    $total_gb = [math]::Round($data.total / 1GB, 2)
                    
                    $current_time = Get-Date
                    $time_diff = ($current_time - $LAST_TIME).TotalSeconds
                    $size_diff = $data.completed - $LAST_SIZE
                    
                    if ($time_diff -gt 0) {
                        $speed = $size_diff / $time_diff / 1MB
                        $remaining = $data.total - $data.completed
                        if ($speed -gt 0) {
                            $eta_seconds = $remaining / $speed / 1MB
                            $eta_min = [math]::Floor($eta_seconds / 60)
                            $eta_sec = [math]::Floor($eta_seconds % 60)
                        } else {
                            $eta_min = "?"
                            $eta_sec = "?"
                        }
                    } else {
                        $speed = 0
                        $eta_min = "?"
                        $eta_sec = "?"
                    }
                    
                    $bar_len = 40
                    $filled = [math]::Floor($bar_len * $percent / 100)
                    $bar = ("█" * $filled) + ("░" * ($bar_len - $filled))
                    
                    Write-Host "`r[$bar] $percent% | $completed_gb/$total_gb GB | 速度：$([math]::Round($speed, 2)) MB/s | 预计：$eta_min`:$eta_sec" -NoNewline
                    
                    $LAST_SIZE = $data.completed
                    $LAST_TIME = $current_time
                }
            } catch {
                # Ignore parse errors
            }
        }
    }
} catch {
    Write-Host "❌ 下载失败：$_" -ForegroundColor Red
}

Write-Host ""
Write-Host "`n📊 当前模型列表:" -ForegroundColor Cyan
$tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags"
foreach ($model in $tags.models) {
    Write-Host "   ✅ $($model.name) - $([math]::Round($model.size/1GB, 2)) GB" -ForegroundColor Green
}
