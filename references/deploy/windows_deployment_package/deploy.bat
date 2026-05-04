@echo off
chcp 65001 > nul

:: 设置日志文件
set LOGFILE=%TEMP%\openclaw_deploy.log
echo ================================ > %LOGFILE%
echo OpenClaw部署开始: %date% %time% >> %LOGFILE%
echo ================================ >> %LOGFILE%

echo ==========================================
echo         OpenClaw Windows自动部署
echo ==========================================
echo 开始时间: %date% %time%
echo 日志文件: %LOGFILE%
echo ==========================================
echo.

:: 函数: 记录日志
:log
echo [%time%] %* >> %LOGFILE%
echo [%time%] %*
echo.
goto :eof

:: 函数: 执行命令并记录
:run_cmd
call :log 执行: %*
%* >> %LOGFILE% 2>&1
if errorlevel 1 (
    call :log ❌ 失败: %*
    exit /b 1
) else (
    call :log ✅ 成功: %*
)
goto :eof

:: 主部署流程
call :log 🔍 步骤1/5: 检查系统环境
ver >> %LOGFILE%
echo 处理器架构: %PROCESSOR_ARCHITECTURE% >> %LOGFILE%

call :log 🔍 步骤2/5: 检查Node.js
node --version > nul 2>&1
if errorlevel 1 (
    call :log ❌ Node.js未安装
    call :log 💡 请先安装Node.js from https://nodejs.org
    call :log 💡 或运行 install_node.js 脚本
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
call :log ✅ Node.js版本: %NODE_VERSION%

call :log 🔍 步骤3/5: 安装OpenClaw
call :run_cmd npm install -g openclaw@latest

call :log 🔍 步骤4/5: 初始化配置
if not exist "%USERPROFILE%\.openclaw" (
    call :run_cmd mkdir "%USERPROFILE%\.openclaw"
)

call :run_cmd openclaw setup

call :log 🔍 步骤5/5: 启动服务
call :log 停止现有OpenClaw服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul >> %LOGFILE%

call :log 启动OpenClaw Gateway服务(端口18789)...
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})" >> %LOGFILE% 2>&1

call :log 等待服务启动...
timeout /t 5 > nul

:: 验证部署
call :log 🔍 验证部署结果...
echo.
echo ==========================================
echo             部署验证
echo ==========================================

powershell -Command "
$ErrorActionPreference = 'Stop'
try {
    Write-Host '测试服务健康检查...' -ForegroundColor Yellow
    $response = Invoke-WebRequest -Uri 'http://localhost:18789/health' -Method Get -TimeoutSec 10
    
    if ($response.StatusCode -eq 200) {
        $health = $response.Content | ConvertFrom-Json
        if ($health.ok) {
            Write-Host '✅ 服务健康检查: 正常' -ForegroundColor Green
            
            # 获取本机IP
            $ip = (Get-NetIPAddress | Where-Object { 
                $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*'
            } | Select-Object -First 1).IPAddress
            
            Write-Host '📍 本地访问: http://localhost:18789' -ForegroundColor Cyan
            Write-Host '🌐 远程访问: http://' + $ip + ':18789' -ForegroundColor Cyan
            Write-Host '📊 健康状态: ' + $health.status -ForegroundColor White
            
            # 写入日志
            Add-Content -Path '%LOGFILE%' -Value '✅ 服务验证成功'
            Add-Content -Path '%LOGFILE%' -Value ('本地访问: http://localhost:18789')
            Add-Content -Path '%LOGFILE%' -Value ('远程访问: http://' + $ip + ':18789')
        } else {
            Write-Host '❌ 服务健康检查: 异常' -ForegroundColor Red
            Add-Content -Path '%LOGFILE%' -Value '❌ 服务健康检查异常'
        }
    } else {
        Write-Host ('❌ HTTP错误: ' + $response.StatusCode) -ForegroundColor Red
        Add-Content -Path '%LOGFILE%' -Value ('❌ HTTP错误: ' + $response.StatusCode)
    }
} catch {
    Write-Host ('❌ 连接错误: ' + $_.Exception.Message) -ForegroundColor Red
    Add-Content -Path '%LOGFILE%' -Value ('❌ 连接错误: ' + $_.Exception.Message)
}
"

echo.
echo ==========================================
echo             部署完成!
echo ==========================================
echo.
echo 📝 部署日志: %LOGFILE%
echo 🌐 访问地址: http://localhost:18789
echo ⏰ 完成时间: %date% %time%
echo.
echo 💡 下一步操作:
echo   • 检查防火墙设置
echo   • 测试远程访问
echo   • 配置所需技能
echo.
pause