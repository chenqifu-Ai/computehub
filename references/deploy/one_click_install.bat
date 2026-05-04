@echo off
chcp 65001 > nul

echo ==========================================
echo    Node.js + OpenClaw 一键安装
echo ==========================================
echo 开始时间: %date% %time%
echo.

:: 检查管理员权限
net session > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 请以管理员身份运行此脚本
    echo 💡 右键点击 - 以管理员身份运行
    pause
    exit /b 1
)

echo ✅ 管理员权限验证通过
echo.

:: 1. 下载Node.js
echo 📦 步骤1/4: 下载Node.js...
powershell -Command "
$progressPreference = 'silentlyContinue'
$url = 'https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi'
$output = '$env:TEMP\\nodejs.msi'
Write-Host '下载Node.js v20.11.1...' -ForegroundColor Yellow
Try {
    Invoke-WebRequest -Uri $url -OutFile $output
    Write-Host '下载完成' -ForegroundColor Green
} Catch {
    Write-Host '下载失败: ' + $_.Exception.Message -ForegroundColor Red
    Exit 1
}
"

if errorlevel 1 (
    echo ❌ Node.js下载失败
    pause
    exit /b 1
)

echo ✅ Node.js下载完成
echo.

:: 2. 安装Node.js
echo ⚙️  步骤2/4: 安装Node.js...
echo     正在安装，请勿关闭窗口...
msiexec /i "%TEMP%\nodejs.msi" /quiet /norestart

echo ⏳ 等待安装完成...
timeout /t 8 > nul

echo 🔄 更新环境变量...
setx PATH "%PATH%;C:\Program Files\nodejs\"

echo ✅ Node.js安装完成
echo.

:: 3. 安装OpenClaw
echo 📦 步骤3/4: 安装OpenClaw...
call npm install -g openclaw@latest

if errorlevel 1 (
    echo ❌ OpenClaw安装失败
    echo 💡 请手动运行: npm install -g openclaw@latest
    pause
    exit /b 1
)

echo ✅ OpenClaw安装完成
echo.

:: 4. 初始化配置
echo ⚙️  步骤4/4: 初始化配置...
if not exist "%USERPROFILE%\.openclaw" mkdir "%USERPROFILE%\.openclaw"
call openclaw setup

echo 🚀 启动OpenClaw服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"

echo ⏳ 等待服务启动...
timeout /t 5 > nul

echo.
echo ==========================================
echo    安装完成!
echo ==========================================
echo ✅ Node.js 已安装
echo ✅ OpenClaw 已安装  
echo ✅ 服务已启动
echo.
echo 🌐 访问地址: http://localhost:18789
echo 📊 健康检查: http://localhost:18789/health
echo.
echo ⏰ 完成时间: %date% %time%
echo.
pause