# Windows RDP远程部署脚本（替代方案）

param(
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    [string]$UserName = "administrator", 
    [Parameter(Mandatory=$true)]
    [string]$Password,
    [int]$RDPPort = 3389
)

function Write-Info {
    Write-Host "[INFO] $($args[0])" -ForegroundColor Green
}

function Write-Warn {
    Write-Host "[WARN] $($args[0])" -ForegroundColor Yellow
}

function Write-Error {
    Write-Host "[ERROR] $($args[0])" -ForegroundColor Red
}

# RDP连接检查
function Test-RDPConnection {
    Write-Info "检查RDP连接: $ComputerName:$RDPPort"
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $result = $tcpClient.BeginConnect($ComputerName, $RDPPort, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(5000)
        $tcpClient.Close()
        
        if ($success) {
            Write-Info "RDP端口可访问"
            return $true
        }
        else {
            Write-Error "RDP连接超时"
            return $false
        }
    }
    catch {
        Write-Error "RDP连接失败: $($_.Exception.Message)"
        return $false
    }
}

# 生成部署批处理文件
function Generate-DeploymentScript {
    $deployScript = @"
@echo off
chcp 65001 >nul

echo ================================
echo OpenClaw Windows自动化部署脚本
echo ================================

REM 检查Node.js
echo 检查Node.js安装...
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js未安装，开始安装...
    
    REM 下载Node.js安装包
    powershell -Command "\`$tempDir = \"%TEMP%\\nodejs-install\"; New-Item -ItemType Directory -Path \`$tempDir -Force | Out-Null; \`$nodeUrl = \"https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi\"; \`$installerPath = \"\`$tempDir\\nodejs.msi\"; Invoke-WebRequest -Uri \`$nodeUrl -OutFile \`$installerPath; Start-Process msiexec -ArgumentList \"/i \`\`"\`$installerPath\`\`" /quiet /norestart\" -Wait"
    
    echo Node.js安装完成
    timeout /t 3
) else (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo Node.js已安装: %NODE_VERSION%
)

REM 安装OpenClaw
echo.
echo 安装OpenClaw...
npm install -g openclaw@latest

REM 初始化配置
echo.
echo 初始化配置...
if not exist "%USERPROFILE%\.openclaw" (
    mkdir "%USERPROFILE%\.openclaw"
)

REM 这里可以添加配置同步逻辑

REM 启动服务
echo.
echo 启动OpenClaw Gateway服务...
start /B node -e "require('openclaw').startGateway({port: 18789})"

echo.
echo 等待服务启动...
timeout /t 5

REM 验证服务
echo.
echo 验证部署...
powershell -Command "try { \`$health = Invoke-RestMethod -Uri 'http://localhost:18789/health' -Method Get; if (\`$health.ok) { echo '✅ 服务正常运行' } else { echo '❌ 服务异常' } } catch { echo '❌ 服务检查失败' }"

echo.
echo ================================
echo 部署完成!
echo Gateway: http://localhost:18789
echo ================================

pause
"@
    
    $scriptPath = "$env:TEMP\\deploy_openclaw.bat"
    Set-Content -Path $scriptPath -Value $deployScript -Encoding UTF8
    return $scriptPath
}

# 使用RDP文件传输
function Copy-FileViaRDP {
    param($LocalPath, $RemotePath)
    
    Write-Info "通过RDP共享复制文件: $LocalPath -> $RemotePath"
    
    try {
        # 创建网络共享路径
        $sharePath = "\\$ComputerName\C$\Users\$UserName\AppData\Local\Temp\"
        
        if (-not (Test-Path $sharePath)) {
            Write-Warn "网络共享不可用，使用备用方案"
            return $false
        }
        
        Copy-Item -Path $LocalPath -Destination $sharePath -Force
        return $true
    }
    catch {
        Write-Warn "文件复制失败: $($_.Exception.Message)"
        return $false
    }
}

# 主部署函数
function Main {
    Write-Host "=== Windows RDP远程部署方案 ===" -ForegroundColor Magenta
    Write-Host "目标设备: $ComputerName" -ForegroundColor Yellow
    Write-Host "RDP端口: $RDPPort" -ForegroundColor Yellow
    
    # 检查RDP连接
    if (-not (Test-RDPConnection)) {
        Write-Error "请确保目标Windows设备:"
        Write-Error "1. 已启用RDP远程桌面"
        Write-Error "2. 防火墙允许RDP连接" 
        Write-Error "3. 有有效的用户凭证"
        return
    }
    
    # 生成部署脚本
    $deployScript = Generate-DeploymentScript
    Write-Info "生成部署脚本: $deployScript"
    
    # 复制脚本到远程设备
    if (Copy-FileViaRDP -LocalPath $deployScript -RemotePath "deploy_openclaw.bat") {
        Write-Info "部署脚本已复制到远程设备"
        
        Write-Host ""
        Write-Host "📋 手动部署步骤:" -ForegroundColor Cyan
        Write-Host "1. 使用RDP连接到: $ComputerName" -ForegroundColor Yellow
        Write-Host "2. 用户名: $UserName" -ForegroundColor Yellow  
        Write-Host "3. 密码: $Password" -ForegroundColor Yellow
        Write-Host "4. 打开文件: C:\\Users\\$UserName\\AppData\\Local\\Temp\\deploy_openclaw.bat" -ForegroundColor Yellow
        Write-Host "5. 以管理员身份运行批处理文件" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "💡 提示: 运行完成后OpenClaw服务将在18789端口启动" -ForegroundColor Green
    }
    else {
        Write-Error "无法自动复制文件，请手动操作:"
        Write-Host "1. 将以下脚本保存为 deploy_openclaw.bat" -ForegroundColor Yellow
        Write-Host "2. 复制到目标设备并运行" -ForegroundColor Yellow
        Write-Host ""
        Get-Content $deployScript | Write-Host -ForegroundColor Gray
    }
    
    # 清理临时文件
    Remove-Item $deployScript -Force -ErrorAction SilentlyContinue
}

# 执行主函数
Main