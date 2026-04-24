# ComputeHub-OPC 性能监控脚本

param(
    [int]$Duration = 300,  # 监控时长(秒)，默认5分钟
    [int]$Interval = 5     # 监控间隔(秒)
)

Write-Host "📊 ComputeHub-OPC 性能监控启动" -ForegroundColor Green
Write-Host "监控时长: $Duration 秒, 间隔: $Interval 秒" -ForegroundColor Yellow
Write-Host ""

# 创建监控目录
$monitorDir = "$env:USERPROFILE\ComputeHub-OPC-Monitor"
if (-not (Test-Path $monitorDir)) {
    New-Item -ItemType Directory -Path $monitorDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$monitorDir\performance_$timestamp.csv"

# CSV文件头
$header = "Timestamp,CPU(%),Memory(MB),NetworkIn(MB),NetworkOut(MB),ActiveConnections,OPCSessions,OPCSubscriptions,DiskIO(MB),ResponseTime(ms),HealthStatus"
Set-Content -Path $logFile -Value $header

Write-Host "📁 监控日志: $logFile" -ForegroundColor Cyan
Write-Host ""

# 获取初始网络统计
$initialNetStats = Get-NetAdapterStatistics -Name "*" | Where-Object { $_.ReceivedBytes -gt 0 -or $_.SentBytes -gt 0 }

# 监控循环
$endTime = (Get-Date).AddSeconds($Duration)
$iteration = 0

while ((Get-Date) -lt $endTime) {
    $iteration++
    $currentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    Write-Host "⏱️  第 $iteration 次采集 [$currentTime]" -ForegroundColor Gray
    
    # 1. 系统级监控
    $cpuUsage = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
    $memoryUsage = [math]::Round((Get-WmiObject -Class Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
    
    # 2. 进程级监控 (查找ComputeHub进程)
    $computeHubProcesses = Get-Process -Name "dotnet" -ErrorAction SilentlyContinue | 
        Where-Object { $_.ProcessName -eq "dotnet" -and $_.CommandLine -like "*ComputeHub*" }
    
    $processMetrics = @{
        CPU = 0
        Memory = 0
        ActiveConnections = 0
    }
    
    if ($computeHubProcesses) {
        $processMetrics.CPU = ($computeHubProcesses | Measure-Object -Property CPU -Sum).Sum
        $processMetrics.Memory = [math]::Round(($computeHubProcesses | Measure-Object -Property WorkingSet -Sum).Sum / 1MB, 2)
    }
    
    # 3. 网络监控
    $currentNetStats = Get-NetAdapterStatistics -Name "*" | Where-Object { $_.ReceivedBytes -gt 0 -or $_.SentBytes -gt 0 }
    $networkIn = [math]::Round(($currentNetStats | Measure-Object -Property ReceivedBytes -Sum).Sum / 1MB, 2)
    $networkOut = [math]::Round(($currentNetStats | Measure-Object -Property SentBytes -Sum).Sum / 1MB, 2)
    
    # 4. OPC服务健康检查
    $healthStatus = "Unknown"
    $responseTime = 0
    
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $healthResponse = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $stopwatch.Stop()
        
        $responseTime = $stopwatch.ElapsedMilliseconds
        if ($healthResponse.StatusCode -eq 200) {
            $healthStatus = "Healthy"
            
            # 尝试获取OPC指标
            try {
                $metricsResponse = Invoke-WebRequest -Uri "http://localhost:5000/metrics" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
                $metricsContent = $metricsResponse.Content
                
                # 解析OPC指标 (示例)
                $opcSessions = if ($metricsContent -match 'opc_sessions_total (\d+)') { $matches[1] } else { "0" }
                $opcSubscriptions = if ($metricsContent -match 'opc_subscriptions_total (\d+)') { $matches[1] } else { "0" }
            } catch {
                $opcSessions = "N/A"
                $opcSubscriptions = "N/A"
            }
        } else {
            $healthStatus = "Unhealthy"
        }
    } catch {
        $healthStatus = "Unreachable"
        $responseTime = 999
    }
    
    # 5. 磁盘IO监控 (简化版)
    $diskIO = 0  # 实际实现需要更复杂的磁盘监控
    
    # 6. 连接数监控 (简化版)
    try {
        $connections = netstat -ano | Select-String ":8080|:4840|:5000" | Measure-Object | Select-Object -ExpandProperty Count
        $processMetrics.ActiveConnections = $connections
    } catch {
        $processMetrics.ActiveConnections = "N/A"
    }
    
    # 构建数据行
    $dataRow = "$currentTime,$cpuUsage,$($processMetrics.Memory),$networkIn,$networkOut,$($processMetrics.ActiveConnections),$opcSessions,$opcSubscriptions,$diskIO,$responseTime,$healthStatus"
    
    # 写入CSV
    Add-Content -Path $logFile -Value $dataRow
    
    # 控制台输出
    Write-Host "  CPU: $cpuUsage% | 内存: $($processMetrics.Memory)MB | 网络: ↓${networkIn}MB ↑${networkOut}MB" -ForegroundColor White
    Write-Host "  连接数: $($processMetrics.ActiveConnections) | 响应时间: ${responseTime}ms | 状态: $healthStatus" -ForegroundColor $(if ($healthStatus -eq 'Healthy') { 'Green' } else { 'Red' })
    
    if ($healthStatus -eq "Healthy") {
        Write-Host "  OPC会话: $opcSessions | OPC订阅: $opcSubscriptions" -ForegroundColor Cyan
    }
    
    Write-Host ""
    
    # 等待下一个间隔
    if ((Get-Date) -lt $endTime) {
        Start-Sleep -Seconds $Interval
    }
}

# 生成性能报告
Write-Host "📈 生成性能分析报告..." -ForegroundColor Green

# 读取监控数据
$monitorData = Import-Csv -Path $logFile

if ($monitorData.Count -gt 0) {
    # 计算统计信息
    $avgCpu = [math]::Round(($monitorData | Measure-Object -Property 'CPU(%)' -Average).Average, 2)
    $avgMemory = [math]::Round(($monitorData | Measure-Object -Property 'Memory(MB)' -Average).Average, 2)
    $avgResponse = [math]::Round(($monitorData | Where-Object { $_.ResponseTime(ms) -ne 999 } | Measure-Object -Property 'ResponseTime(ms)' -Average).Average, 2)
    
    $healthyCount = ($monitorData | Where-Object { $_.HealthStatus -eq 'Healthy' }).Count
    $availability = [math]::Round(($healthyCount / $monitorData.Count) * 100, 2)
    
    Write-Host ""
    Write-Host "📊 性能统计摘要:" -ForegroundColor Cyan
    Write-Host "  ==============================="
    Write-Host "  监控时长: $Duration 秒"
    Write-Host "  数据点数: $($monitorData.Count)"
    Write-Host "  平均CPU使用率: ${avgCpu}%"
    Write-Host "  平均内存使用: ${avgMemory}MB"
    Write-Host "  平均响应时间: ${avgResponse}ms"
    Write-Host "  服务可用性: ${availability}%"
    Write-Host "  ==============================="
    
    # 检查性能问题
    $issues = @()
    
    if ($avgCpu -gt 80) {
        $issues += "⚠️  CPU使用率较高(超过80%)"
    }
    
    if ($avgResponse -gt 1000) {
        $issues += "⚠️  响应时间较慢(超过1000ms)"
    }
    
    if ($availability -lt 99.9) {
        $issues += "⚠️  可用性低于99.9%"
    }
    
    if ($issues.Count -gt 0) {
        Write-Host ""
        Write-Host "🔴 发现性能问题:" -ForegroundColor Red
        foreach ($issue in $issues) {
            Write-Host "  - $issue" -ForegroundColor Red
        }
    } else {
        Write-Host ""
        Write-Host "✅ 性能表现良好" -ForegroundColor Green
    }
    
    # 生成图表脚本
    $chartScript = @"
# 性能数据可视化脚本
# 使用方法: 在PowerShell中运行此脚本

\$data = Import-Csv -Path "$logFile"

# 安装必要的模块(如果需要)
if (-not (Get-Module -Name ImportExcel -ListAvailable)) {
    Install-Module -Name ImportExcel -Force -Scope CurrentUser
}

# 创建Excel报告
\$excelFile = "$monitorDir\performance_report_$timestamp.xlsx"
\$data | Export-Excel -Path \$excelFile -WorksheetName "性能数据" -AutoSize -AutoFilter

Write-Host "📊 Excel报告已生成: \$excelFile"

# 简单控制台图表函数
function Show-SimpleChart {
    param([array]\$values, [string]\$title, [string]\$unit)
    
    \$maxValue = (\$values | Measure-Object -Maximum).Maximum
    \$scale = 50 / \$maxValue
    
    Write-Host "\`n\$title:" -ForegroundColor Cyan
    foreach (\$value in \$values) {
        \$bars = [math]::Round(\$value * \$scale)
        Write-Host ("{0,6}\$unit |" -f \$value) -NoNewline
        Write-Host ("█" * \$bars) -ForegroundColor Green -NoNewline
        Write-Host ("-" * (50 - \$bars)) -ForegroundColor Gray
    }
}

# 显示CPU使用率图表
Show-SimpleChart -values \$data.'CPU(%)' -title "CPU使用率趋势" -unit "%"
"@
    
    Set-Content -Path "$monitorDir\generate_charts.ps1" -Value $chartScript
    
    Write-Host ""
    Write-Host "📈 图表生成脚本: $monitorDir\generate_charts.ps1" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ 性能监控完成!" -ForegroundColor Green
Write-Host "📁 监控数据保存在: $monitorDir" -ForegroundColor Cyan
Write-Host "⏰ 总监控时长: $Duration 秒 ($([math]::Round($Duration/60, 1)) 分钟)" -ForegroundColor Yellow