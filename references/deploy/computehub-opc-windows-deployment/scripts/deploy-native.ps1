# ComputeHub-OPC .NET原生部署脚本
# 适用于Windows开发测试环境

Write-Host "🚀 开始部署 ComputeHub-OPC v1.0.0 (.NET原生方式)" -ForegroundColor Green

# 检查.NET运行时
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    Write-Host "❌ .NET运行时未安装，正在安装..." -ForegroundColor Red
    
    # 安装.NET 8.0运行时
    winget install Microsoft.DotNet.Runtime.8 -e --accept-package-agreements --accept-source-agreements
    
    Write-Host "✅ .NET运行时安装完成" -ForegroundColor Green
}

# 检查.NET版本
$dotnetVersion = dotnet --version
Write-Host "✅ .NET版本: $dotnetVersion" -ForegroundColor Green

# 创建部署目录
$deployDir = "$env:USERPROFILE\ComputeHub-OPC-Native"
if (-not (Test-Path $deployDir)) {
    New-Item -ItemType Directory -Path $deployDir -Force | Out-Null
}
Set-Location $deployDir

Write-Host "📁 部署目录: $deployDir" -ForegroundColor Yellow

# 提示用户下载发布包
Write-Host ""
Write-Host "📦 请执行以下步骤:" -ForegroundColor Cyan
Write-Host "1. 从官方发布页面下载 ComputeHub-OPC v1.0.0 发布包"
Write-Host "2. 解压到当前目录: $deployDir"
Write-Host "3. 确保包含以下文件:"
Write-Host "   - ComputeHub.OPC.Server.dll"
Write-Host "   - appsettings.json"
Write-Host "   - 所有依赖的.dll文件"
Write-Host ""

# 等待用户确认
$confirm = Read-Host "是否已准备好发布文件? (y/n)"
if ($confirm -ne 'y') {
    Write-Host "❌ 请先准备发布文件后再运行此脚本" -ForegroundColor Red
    exit 1
}

# 检查必要文件
$requiredFiles = @("ComputeHub.OPC.Server.dll", "appsettings.json")
$missingFiles = @()

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ 缺少必要文件: $($missingFiles -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 必要文件检查通过" -ForegroundColor Green

# 创建配置文件（如果不存在）
if (-not (Test-Path "appsettings.Production.json")) {
    $appSettingsContent = @"
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft": "Warning",
      "Microsoft.Hosting.Lifetime": "Information"
    }
  },
  "AllowedHosts": "*",
  "Kestrel": {
    "Endpoints": {
      "Http": {
        "Url": "http://0.0.0.0:8080"
      },
      "OpcUa": {
        "Url": "opc.tcp://0.0.0.0:4840"
      }
    },
    "Limits": {
      "MaxConcurrentConnections": 100,
      "MaxConcurrentUpgradedConnections": 100
    }
  },
  "OPC": {
    "ServerName": "ComputeHub-OPC-Server",
    "ApplicationUri": "urn:localhost:ComputeHubOPC",
    "ProductUri": "https://computehub.com/opc",
    "MaxSessions": 50,
    "MaxSubscriptionsPerSession": 100,
    "MaxNodesPerRead": 1000,
    "MaxNodesPerWrite": 1000,
    "PublishingInterval": 1000,
    "SamplingInterval": 500,
    "SessionTimeout": 600
  },
  "Metrics": {
    "Enabled": true,
    "Port": 5000
  }
}
"@
    
    Set-Content -Path "appsettings.Production.json" -Value $appSettingsContent
    Write-Host "✅ 生产环境配置文件创建完成" -ForegroundColor Green
}

# 创建日志目录
New-Item -ItemType Directory -Path "./logs" -Force | Out-Null

# 创建启动脚本
$startScriptContent = @"
@echo off
echo 🚀 启动 ComputeHub-OPC 服务器
echo.

# 设置环境变量
set ASPNETCORE_ENVIRONMENT=Production
set DOTNET_PRINT_TELEMETRY_MESSAGE=false

# 启动服务器
echo 启动时间: %date% %time%
echo.

dotnet ComputeHub.OPC.Server.dll --urls "http://0.0.0.0:8080"

if %errorlevel% neq 0 (
    echo ❌ 服务器启动失败
    pause
    exit /b 1
)
"@

Set-Content -Path "start-server.bat" -Value $startScriptContent

# 创建服务管理脚本
$serviceScriptContent = @"
# ComputeHub-OPC 服务管理脚本

param(
    [string]\$Action = "start"
)

\$serviceName = "ComputeHubOPC"
\$serviceDisplayName = "ComputeHub OPC UA Server"
\$serviceDescription = "ComputeHub OPC UA Server for industrial data exchange"
\$executablePath = "\$PSScriptRoot\start-server.bat"

switch (\$Action) {
    "install" {
        # 安装为Windows服务
        if (Get-Service -Name \$serviceName -ErrorAction SilentlyContinue) {
            Write-Host "服务 \$serviceName 已存在" -ForegroundColor Yellow
        } else {
            New-Service -Name \$serviceName \
                        -DisplayName \$serviceDisplayName \
                        -Description \$serviceDescription \
                        -BinaryPathName \$executablePath \
                        -StartupType Automatic
            Write-Host "✅ 服务安装完成" -ForegroundColor Green
        }
    }
    
    "uninstall" {
        # 卸载服务
        if (Get-Service -Name \$serviceName -ErrorAction SilentlyContinue) {
            Stop-Service -Name \$serviceName -Force
            Start-Sleep -Seconds 2
            sc.exe delete \$serviceName
            Write-Host "✅ 服务卸载完成" -ForegroundColor Green
        } else {
            Write-Host "服务 \$serviceName 不存在" -ForegroundColor Yellow
        }
    }
    
    "start" {
        # 直接启动（非服务方式）
        Write-Host "🚀 启动 ComputeHub-OPC 服务器..." -ForegroundColor Green
        .\start-server.bat
    }
    
    default {
        Write-Host "用法: .\manage-service.ps1 [install|uninstall|start]" -ForegroundColor Cyan
    }
}
"@

Set-Content -Path "manage-service.ps1" -Value $serviceScriptContent

# 配置防火墙
Write-Host "🔥 配置防火墙规则..." -ForegroundColor Yellow
try {
    # 开放OPC UA端口
    New-NetFirewallRule -DisplayName "ComputeHub-OPC OPC UA" -Direction Inbound -LocalPort 4840 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    
    # 开放管理界面端口  
    New-NetFirewallRule -DisplayName "ComputeHub-OPC Web Console" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    
    # 开放监控端口
    New-NetFirewallRule -DisplayName "ComputeHub-OPC Monitoring" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    
    Write-Host "✅ 防火墙规则配置完成" -ForegroundColor Green
} catch {
    Write-Host "⚠️  防火墙配置可能需要管理员权限" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 .NET原生部署准备完成!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 启动方式:" -ForegroundColor Cyan
Write-Host "  直接运行: .\start-server.bat"
Write-Host "  或使用PowerShell: .\manage-service.ps1 start"
Write-Host ""
Write-Host "🔧 服务管理:" -ForegroundColor Cyan
Write-Host "  安装为服务: .\manage-service.ps1 install"
Write-Host "  卸载服务: .\manage-service.ps1 uninstall"
Write-Host ""
Write-Host "📊 访问地址:" -ForegroundColor Cyan
Write-Host "  管理界面: http://localhost:8080"
Write-Host "  OPC UA端点: opc.tcp://localhost:4840"
Write-Host "  健康检查: http://localhost:5000/health"
Write-Host ""
Write-Host "⚠️  注意事项:" -ForegroundColor Yellow
Write-Host "  - 确保.NET 8.0运行时已安装"
Write-Host "  - 首次运行可能需要下载NuGet包"
Write-Host "  - 生产环境建议使用Docker部署"

Write-Host "✅ 原生部署脚本完成!" -ForegroundColor Green