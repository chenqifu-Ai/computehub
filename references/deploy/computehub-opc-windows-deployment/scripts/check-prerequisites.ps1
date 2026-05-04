# ComputeHub-OPC 环境检查脚本

Write-Host "🔍 检查 ComputeHub-OPC 部署环境要求" -ForegroundColor Green
Write-Host ""

# 系统信息
$osInfo = Get-WmiObject -Class Win32_OperatingSystem
$computerInfo = Get-WmiObject -Class Win32_ComputerSystem

Write-Host "🖥️  系统信息:" -ForegroundColor Cyan
Write-Host "  操作系统: $($osInfo.Caption)"
Write-Host "  版本: $($osInfo.Version)"
Write-Host "  架构: $($osInfo.OSArchitecture)"
Write-Host "  内存: $([math]::Round($computerInfo.TotalPhysicalMemory / 1GB, 2)) GB"
Write-Host "  处理器: $($computerInfo.NumberOfProcessors) 核心"
Write-Host ""

# 检查要求
$requirements = @{}

# 1. 检查.NET运行时
if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    $dotnetVersion = dotnet --version
    $requirements[".NET Runtime"] = @{
        Status = "✅";
        Version = $dotnetVersion;
        Message = "已安装"
    }
} else {
    $requirements[".NET Runtime"] = @{
        Status = "❌";
        Version = "未安装";
        Message = "需要安装.NET 8.0+"
    }
}

# 2. 检查Docker
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerVersion = docker --version
    $requirements["Docker"] = @{
        Status = "✅";
        Version = $dockerVersion;
        Message = "已安装"
    }
    
    # 检查Docker服务状态
    try {
        $dockerInfo = docker info 2>$null
        if ($LASTEXITCODE -eq 0) {
            $requirements["Docker Service"] = @{
                Status = "✅";
                Version = "运行中";
                Message = "服务正常"
            }
        } else {
            $requirements["Docker Service"] = @{
                Status = "❌";
                Version = "未运行";
                Message = "需要启动Docker服务"
            }
        }
    } catch {
        $requirements["Docker Service"] = @{
            Status = "❌";
            Version = "错误";
            Message = "服务异常: $_"
        }
    }
} else {
    $requirements["Docker"] = @{
        Status = "❌";
        Version = "未安装";
        Message = "可选安装"
    }
}

# 3. 检查可用端口
$portsToCheck = @(4840, 8080, 5000, 9090)
$portStatus = @{}

foreach ($port in $portsToCheck) {
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $port)
        $listener.Start()
        $listener.Stop()
        $portStatus[$port] = @{ Status = "✅"; Message = "可用" }
    } catch {
        $portStatus[$port] = @{ Status = "❌"; Message = "被占用" }
    }
}

$requirements["端口检查"] = @{
    Status = "🔍";
    Version = "多端口";
    Message = "详见下方详细检查"
}

# 4. 检查磁盘空间
$diskInfo = Get-PSDrive C
$freeSpaceGB = [math]::Round($diskInfo.Free / 1GB, 2)
$totalSpaceGB = [math]::Round($diskInfo.Used / 1GB + $diskInfo.Free / 1GB, 2)

if ($freeSpaceGB -ge 10) {
    $requirements["磁盘空间"] = @{
        Status = "✅";
        Version = "${freeSpaceGB}GB/${totalSpaceGB}GB";
        Message = "充足"
    }
} else {
    $requirements["磁盘空间"] = @{
        Status = "⚠️ ";
        Version = "${freeSpaceGB}GB/${totalSpaceGB}GB";
        Message = "建议至少10GB空闲空间"
    }
}

# 5. 检查防火墙状态
$firewallStatus = Get-Service -Name mpssvc -ErrorAction SilentlyContinue
if ($firewallStatus.Status -eq 'Running') {
    $requirements["Windows防火墙"] = @{
        Status = "✅";
        Version = "运行中";
        Message = "已启用"
    }
} else {
    $requirements["Windows防火墙"] = @{
        Status = "⚠️ ";
        Version = "未运行";
        Message = "建议启用防火墙"
    }
}

# 输出检查结果
Write-Host "📋 环境要求检查:" -ForegroundColor Cyan
Write-Host ""

foreach ($req in $requirements.GetEnumerator()) {
    Write-Host "  $($req.Value.Status) $($req.Key): $($req.Value.Version) - $($req.Value.Message)" -ForegroundColor $(if ($req.Value.Status -eq '✅') { 'Green' } elseif ($req.Value.Status -eq '❌') { 'Red' } else { 'Yellow' })
}

Write-Host ""
Write-Host "🔍 端口详细检查:" -ForegroundColor Cyan
foreach ($port in $portStatus.GetEnumerator()) {
    Write-Host "  端口 $($port.Key): $($port.Value.Status) $($port.Value.Message)" -ForegroundColor $(if ($port.Value.Status -eq '✅') { 'Green' } else { 'Red' })
}

Write-Host ""
Write-Host "💡 部署建议:" -ForegroundColor Cyan

# 根据检查结果给出建议
$missingRequirements = $requirements.Values | Where-Object { $_.Status -eq '❌' }

if ($missingRequirements.Count -eq 0) {
    Write-Host "  ✅ 环境满足所有要求，可以开始部署!" -ForegroundColor Green
    Write-Host "  推荐部署方式: Docker (生产) 或 .NET原生 (开发)" -ForegroundColor Yellow
} else {
    Write-Host "  ⚠️  以下要求未满足:" -ForegroundColor Yellow
    foreach ($missing in $missingRequirements) {
        $reqName = $requirements.GetEnumerator() | Where-Object { $_.Value -eq $missing } | Select-Object -First 1 -ExpandProperty Key
        Write-Host "    - $reqName: $($missing.Message)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "  🔧 修复建议:" -ForegroundColor Cyan
    
    if ($requirements[".NET Runtime"].Status -eq '❌') {
        Write-Host "    - 安装.NET 8.0: winget install Microsoft.DotNet.Runtime.8" -ForegroundColor White
    }
    
    if ($requirements["Docker"].Status -eq '❌' -and $requirements["Docker"].Message -ne '可选安装') {
        Write-Host "    - 安装Docker: winget install Docker.DockerDesktop" -ForegroundColor White
    }
    
    if ($requirements["Docker Service"].Status -eq '❌') {
        Write-Host "    - 启动Docker服务: Start-Service Docker" -ForegroundColor White
    }
    
    # 检查被占用的端口
    $occupiedPorts = $portStatus.GetEnumerator() | Where-Object { $_.Value.Status -eq '❌' } | Select-Object -ExpandProperty Key
    if ($occupiedPorts.Count -gt 0) {
        Write-Host "    - 以下端口被占用: $($occupiedPorts -join ', ')" -ForegroundColor White
        Write-Host "    - 可以修改部署配置使用其他端口" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "🚀 下一步操作:" -ForegroundColor Green
Write-Host "  1. 修复上述问题(如有)"
Write-Host "  2. 选择部署方式:"
Write-Host "     - Docker部署: .\deploy-docker.ps1"
Write-Host "     - .NET原生部署: .\deploy-native.ps1"
Write-Host "     - Windows服务部署: .\deploy-service.ps1"
Write-Host "  3. 运行选择的部署脚本"

# 返回退出代码
if ($missingRequirements.Count -eq 0) {
    exit 0
} else {
    exit 1
}