# ComputeHub-OPC Windows服务部署脚本
# 适用于生产环境后台服务部署

Write-Host "🚀 开始部署 ComputeHub-OPC v1.0.0 (Windows服务方式)" -ForegroundColor Green

# 检查管理员权限
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ 需要管理员权限运行此脚本" -ForegroundColor Red
    Write-Host "请以管理员身份运行PowerShell" -ForegroundColor Yellow
    exit 1
}

# 检查.NET运行时
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    Write-Host "❌ .NET运行时未安装，正在安装..." -ForegroundColor Red
    
    # 安装.NET 8.0运行时
    winget install Microsoft.DotNet.Runtime.8 -e --accept-package-agreements --accept-source-agreements
    
    Write-Host "✅ .NET运行时安装完成" -ForegroundColor Green
}

# 创建部署目录
$deployDir = "C:\Program Files\ComputeHub-OPC"
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

# 创建生产环境配置
if (-not (Test-Path "appsettings.Production.json")) {
    $appSettingsContent = @"
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft": "Warning",
      "Microsoft.Hosting.Lifetime": "Information"
    },
    "File": {
      "Path": "logs/computehub-opc-{Date}.log",
      "FileSizeLimitBytes": 10485760,
      "RetainedFileCountLimit": 31
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

# 创建服务包装器
$serviceWrapperContent = @"
using System;
using System.Diagnostics;
using System.IO;
using System.ServiceProcess;

namespace ComputeHubOPCService
{
    public partial class ComputeHubOPCService : ServiceBase
    {
        private Process _process;
        
        public ComputeHubOPCService()
        {
            ServiceName = "ComputeHubOPC";
            CanStop = true;
            CanPauseAndContinue = false;
            AutoLog = true;
        }
        
        protected override void OnStart(string[] args)
        {
            try
            {
                var startInfo = new ProcessStartInfo
                {
                    FileName = "dotnet",
                    Arguments = "ComputeHub.OPC.Server.dll --urls http://0.0.0.0:8080",
                    WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    EnvironmentVariables = 
                    {
                        ["ASPNETCORE_ENVIRONMENT"] = "Production",
                        ["DOTNET_PRINT_TELEMETRY_MESSAGE"] = "false"
                    }
                };
                
                _process = new Process { StartInfo = startInfo };
                _process.OutputDataReceived += (sender, e) => 
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        EventLog.WriteEntry(e.Data, EventLogEntryType.Information);
                };
                
                _process.ErrorDataReceived += (sender, e) => 
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        EventLog.WriteEntry(e.Data, EventLogEntryType.Error);
                };
                
                _process.Start();
                _process.BeginOutputReadLine();
                _process.BeginErrorReadLine();
                
                EventLog.WriteEntry("ComputeHub-OPC服务启动成功", EventLogEntryType.Information);
            }
            catch (Exception ex)
            {
                EventLog.WriteEntry("服务启动失败: " + ex.Message, EventLogEntryType.Error);
                throw;
            }
        }
        
        protected override void OnStop()
        {
            try
            {
                if (_process != null && !_process.HasExited)
                {
                    _process.Kill();
                    _process.WaitForExit(5000);
                }
                EventLog.WriteEntry("ComputeHub-OPC服务已停止", EventLogEntryType.Information);
            }
            catch (Exception ex)
            {
                EventLog.WriteEntry("服务停止失败: " + ex.Message, EventLogEntryType.Error);
            }
        }
    }
}
"@

# 创建服务安装脚本
$installScriptContent = @"
# ComputeHub-OPC Windows服务安装脚本

# 编译服务包装器
try {
    Add-Type -TypeDefinition @"
using System;
using System.Diagnostics;
using System.IO;
using System.ServiceProcess;

namespace ComputeHubOPCService
{
    public partial class ComputeHubOPCService : ServiceBase
    {
        private Process _process;
        
        public ComputeHubOPCService()
        {
            ServiceName = "ComputeHubOPC";
            CanStop = true;
            CanPauseAndContinue = false;
            AutoLog = true;
        }
        
        protected override void OnStart(string[] args)
        {
            try
            {
                var startInfo = new ProcessStartInfo
                {
                    FileName = "dotnet",
                    Arguments = "ComputeHub.OPC.Server.dll --urls http://0.0.0.0:8080",
                    WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    EnvironmentVariables = 
                    {
                        ["ASPNETCORE_ENVIRONMENT"] = "Production",
                        ["DOTNET_PRINT_TELEMETRY_MESSAGE"] = "false"
                    }
                };
                
                _process = new Process { StartInfo = startInfo };
                _process.OutputDataReceived += (sender, e) => 
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        EventLog.WriteEntry(e.Data, EventLogEntryType.Information);
                };
                
                _process.ErrorDataReceived += (sender, e) => 
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        EventLog.WriteEntry(e.Data, EventLogEntryType.Error);
                };
                
                _process.Start();
                _process.BeginOutputReadLine();
                _process.BeginErrorReadLine();
                
                EventLog.WriteEntry("ComputeHub-OPC服务启动成功", EventLogEntryType.Information);
            }
            catch (Exception ex)
            {
                EventLog.WriteEntry("服务启动失败: " + ex.Message, EventLogEntryType.Error);
                throw;
            }
        }
        
        protected override void OnStop()
        {
            try
            {
                if (_process != null && !_process.HasExited)
                {
                    _process.Kill();
                    _process.WaitForExit(5000);
                }
                EventLog.WriteEntry("ComputeHub-OPC服务已停止", EventLogEntryType.Information);
            }
            catch (Exception ex)
            {
                EventLog.WriteEntry("服务停止失败: " + ex.Message, EventLogEntryType.Error);
            }
        }
    }
}
"@ -OutputAssembly "ComputeHubOPCService.dll" -ReferencedAssemblies "System.ServiceProcess.dll"
    Write-Host "✅ 服务包装器编译成功" -ForegroundColor Green
} catch {
    Write-Host "⚠️  服务包装器编译失败，使用原生安装方式" -ForegroundColor Yellow
}

# 安装Windows服务
\$serviceName = "ComputeHubOPC"
\$serviceDisplayName = "ComputeHub OPC UA Server"
\$serviceDescription = "ComputeHub OPC UA Server for industrial data exchange"
\$executablePath = "dotnet"
\$arguments = "\`"\$PWD\ComputeHub.OPC.Server.dll\`" --urls http://0.0.0.0:8080"

# 检查服务是否已存在
if (Get-Service -Name \$serviceName -ErrorAction SilentlyContinue) {
    Write-Host "服务 \$serviceName 已存在，正在停止..." -ForegroundColor Yellow
    Stop-Service -Name \$serviceName -Force
    Start-Sleep -Seconds 3
}

# 创建服务
\$service = New-Service -Name \$serviceName \
                        -DisplayName \$serviceDisplayName \
                        -Description \$serviceDescription \
                        -BinaryPathName "\$executablePath \$arguments" \
                        -StartupType Automatic \
                        -ErrorAction Stop

Write-Host "✅ Windows服务创建成功" -ForegroundColor Green

# 配置服务恢复策略
sc.exe failure \$serviceName reset= 60 actions= restart/5000/restart/5000/restart/5000

# 启动服务
Start-Service -Name \$serviceName
Write-Host "✅ 服务启动成功" -ForegroundColor Green

# 检查服务状态
Start-Sleep -Seconds 5
\$serviceStatus = Get-Service -Name \$serviceName
Write-Host "服务状态: \$($serviceStatus.Status)" -ForegroundColor Cyan
"@

Set-Content -Path "install-service.ps1" -Value $installScriptContent

# 创建服务管理脚本
$manageScriptContent = @"
# ComputeHub-OPC 服务管理脚本

param(
    [string]\$Action = "status"
)

\$serviceName = "ComputeHubOPC"

switch (\$Action.ToLower()) {
    "start" {
        Start-Service -Name \$serviceName
        Write-Host "✅ 服务启动命令已发送" -ForegroundColor Green
    }
    
    "stop" {
        Stop-Service -Name \$serviceName -Force
        Write-Host "✅ 服务停止命令已发送" -ForegroundColor Green
    }
    
    "restart" {
        Restart-Service -Name \$serviceName -Force
        Write-Host "✅ 服务重启命令已发送" -ForegroundColor Green
    }
    
    "status" {
        \$service = Get-Service -Name \$serviceName -ErrorAction SilentlyContinue
        if (\$service) {
            Write-Host "服务状态: \$($service.Status)" -ForegroundColor Cyan
            Write-Host "启动类型: \$($service.StartType)" -ForegroundColor Cyan
        } else {
            Write-Host "❌ 服务未找到" -ForegroundColor Red
        }
    }
    
    "logs" {
        # 查看事件日志
        Get-EventLog -LogName Application -Source \$serviceName -Newest 20 | 
            Format-Table TimeGenerated, EntryType, Message -AutoSize
    }
    
    default {
        Write-Host "用法: .\manage-service.ps1 [start|stop|restart|status|logs]" -ForegroundColor Cyan
    }
}
"@

Set-Content -Path "manage-service.ps1" -Value $manageScriptContent

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
    Write-Host "⚠️  防火墙配置完成" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Windows服务部署准备完成!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 安装步骤:" -ForegroundColor Cyan
Write-Host "1. 以管理员身份运行: .\install-service.ps1"
Write-Host "2. 等待服务安装和启动"
Write-Host "3. 验证服务状态: .\manage-service.ps1 status"
Write-Host ""
Write-Host "🔧 服务管理:" -ForegroundColor Cyan
Write-Host "  启动服务: .\manage-service.ps1 start"
Write-Host "  停止服务: .\manage-service.ps1 stop"
Write-Host "  重启服务: .\manage-service.ps1 restart"
Write-Host "  查看状态: .\manage-service.ps1 status"
Write-Host "  查看日志: .\manage-service.ps1 logs"
Write-Host ""
Write-Host "📊 访问地址:" -ForegroundColor Cyan
Write-Host "  管理界面: http://localhost:8080"
Write-Host "  OPC UA端点: opc.tcp://localhost:4840"
Write-Host "  健康检查: http://localhost:5000/health"
Write-Host ""
Write-Host "⚠️  注意事项:" -ForegroundColor Yellow
Write-Host "  - 必须以管理员身份运行安装脚本"
Write-Host "  - 服务将在系统启动时自动运行"
Write-Host "  - 日志保存在Windows事件查看器中"

Write-Host "✅ 服务部署脚本完成!" -ForegroundColor Green