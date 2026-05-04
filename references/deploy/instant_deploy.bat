@echo off
echo 🚀 OpenClaw一键部署
echo ⏱️  开始时间: %date% %time%
echo.

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 请先安装Node.js: https://nodejs.org
    pause
    exit /b 1
)

echo ✅ Node.js已安装
echo 📦 安装OpenClaw...
npm install -g openclaw@latest

echo ⚙️  初始化配置...
if not exist "%USERPROFILE%\.openclaw" mkdir "%USERPROFILE%\.openclaw"
openclaw setup

echo 🚀 启动服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"

echo ⏳ 等待启动...
timeout /t 3 >nul

echo ✅ 部署完成!
echo 🌐 访问: http://localhost:18789
echo 📊 验证: http://localhost:18789/health
echo.
echo 💡 以管理员身份运行以获得最佳效果
echo ⏰ 完成时间: %date% %time%
pause