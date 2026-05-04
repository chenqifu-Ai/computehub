@echo off
chcp 65001 > nul

echo ====================================
echo      Node.js 自动安装脚本
echo ====================================
echo.

echo 正在下载Node.js安装包...
echo.

:: 创建临时目录
set TEMP_DIR=%TEMP%\nodejs_install
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: 下载Node.js
powershell -Command "
$progressPreference = 'silentlyContinue'
$url = 'https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi'
$output = '%TEMP_DIR%\\nodejs.msi'

Write-Host '下载Node.js v20.11.1...' -ForegroundColor Yellow
Try {
    Invoke-WebRequest -Uri $url -OutFile $output
    Write-Host '✅ 下载完成' -ForegroundColor Green
    Write-Host '文件位置: ' + $output -ForegroundColor Cyan
} Catch {
    Write-Host '❌ 下载失败: ' + $_.Exception.Message -ForegroundColor Red
    Exit 1
}
"

if errorlevel 1 (
    echo ❌ Node.js下载失败
    pause
    exit /b 1
)

echo.
echo 开始安装Node.js...
echo 请等待安装完成（大约2-3分钟）...
echo.

:: 安装Node.js
msiexec /i "%TEMP_DIR%\nodejs.msi" /quiet /norestart

:: 等待安装完成
echo 等待安装完成...
timeout /t 10

echo.
echo 更新环境变量...
setx PATH "%PATH%;C:\Program Files\nodejs\"

echo.
echo 验证安装...
node --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js安装失败
    echo 请手动从 https://nodejs.org 下载安装
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✅ Node.js安装成功: %NODE_VERSION%

echo.
echo 验证npm...
npm --version > nul 2>&1
if errorlevel 1 (
    echo ⚠️  npm验证失败，但Node.js已安装
) else (
    for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
    echo ✅ npm版本: %NPM_VERSION%
)

echo.
echo ====================================
echo     Node.js安装完成!
echo ====================================
echo.
echo 💡 下一步:
echo   1. 重新打开命令提示符
echo   2. 运行 deploy.bat 继续OpenClaw部署
echo.
echo 🎯 或者直接运行:
echo   npm install -g openclaw@latest
echo   openclaw setup
echo.
pause