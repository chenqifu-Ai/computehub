@echo off
chcp 65001 > nul

echo ====================================
echo    OpenClaw Windows自动部署脚本
echo ====================================
echo.

echo 1. 检查系统架构...
if "%PROCESSOR_ARCHITECTURE%" == "AMD64" (
    echo   ✅ 64位系统
) else (
    echo   ⚠️  32位系统 - 可能需要特定版本
)

echo.
echo 2. 检查Node.js安装...
node --version > nul 2>&1
if errorlevel 1 (
    echo   ❌ Node.js未安装
    echo   请从 https://nodejs.org 下载安装Node.js 20+
    echo   安装完成后重新运行此脚本
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo   ✅ Node.js已安装: %NODE_VERSION%
)

echo.
echo 3. 安装OpenClaw...
echo   正在安装OpenClaw最新版本...
npm install -g openclaw@latest

if errorlevel 1 (
    echo   ❌ OpenClaw安装失败
    echo   请检查网络连接或npm配置
    pause
    exit /b 1
) else (
    echo   ✅ OpenClaw安装成功
)

echo.
echo 4. 初始化配置...
if not exist "%USERPROFILE%\.openclaw" (
    mkdir "%USERPROFILE%\.openclaw"
    echo   创建配置目录: %USERPROFILE%\.openclaw
)

echo   运行初始化设置...
openclaw setup

echo.
echo 5. 启动OpenClaw服务...
echo   停止现有服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul

echo   启动Gateway服务(端口18789)...
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"

echo   等待服务启动...
timeout /t 5

echo.
echo 6. 验证部署...
echo   检查服务状态:
powershell -Command "
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:18789/health' -Method Get -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $health = $response.Content | ConvertFrom-Json
        if ($health.ok) { 
            Write-Host '✅ 服务正常运行' -ForegroundColor Green
            Write-Host '📍 访问地址: http://localhost:18789' -ForegroundColor Yellow
            Write-Host '🌐 远程访问: http://' + (Get-NetIPAddress | Where-Object { $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -ne '127.0.0.1' } | Select-Object -First 1).IPAddress + ':18789' -ForegroundColor Cyan
        } else {
            Write-Host '❌ 服务返回异常状态' -ForegroundColor Red
        }
    } else {
        Write-Host ('❌ HTTP错误: ' + $response.StatusCode) -ForegroundColor Red
    }
} catch {
    Write-Host ('❌ 连接错误: ' + $_.Exception.Message) -ForegroundColor Red
}
"

echo.
echo ====================================
echo   部署完成!
echo ====================================
echo.
echo 下一步操作:
echo   • 检查防火墙是否开放18789端口
echo   • 测试远程访问
echo   • 配置需要的技能和设置
echo.
pause