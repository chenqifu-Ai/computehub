@echo off
chcp 65001 > nul

echo ================================
echo OpenClaw Windows本地自动化部署脚本
echo ================================

echo 检查系统架构...
if "%PROCESSOR_ARCHITECTURE%" == "AMD64" (
    echo 64位系统检测通过
) else (
    echo 32位系统，可能需要调整安装包
)

echo.
echo 检查Node.js安装...
node --version > nul 2>&1
if errorlevel 1 (
    echo Node.js未安装，开始安装...
    
    REM 创建临时目录
    set TEMP_DIR=%TEMP%\nodejs-install
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    
    REM 下载Node.js安装包
    echo 下载Node.js安装包...
    powershell -Command "$url = 'https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi'; $output = '%TEMP_DIR%\nodejs.msi'; Invoke-WebRequest -Uri $url -OutFile $output"
    
    if exist "%TEMP_DIR%\nodejs.msi" (
        echo 开始安装Node.js...
        msiexec /i "%TEMP_DIR%\nodejs.msi" /quiet /norestart
        
        echo 等待安装完成...
        timeout /t 10
        
        echo 更新环境变量...
        setx PATH "%PATH%;C:\Program Files\nodejs\"
    ) else (
        echo ❌ Node.js下载失败
        pause
        exit /b 1
    )
) else (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo Node.js已安装: %NODE_VERSION%
)

echo.
echo 安装OpenClaw...
npm install -g openclaw@latest

if errorlevel 1 (
    echo ❌ OpenClaw安装失败
    pause
    exit /b 1
)

echo.
echo 初始化配置目录...
if not exist "%USERPROFILE%\.openclaw" (
    mkdir "%USERPROFILE%\.openclaw"
    echo 创建配置目录: %USERPROFILE%\.openclaw
)

echo.
echo 运行OpenClaw初始化...
openclaw setup

echo.
echo 启动OpenClaw Gateway服务...

REM 停止现有服务
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul

REM 启动新服务
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"

echo 等待服务启动...
timeout /t 5

echo.
echo 验证服务状态...
powershell -Command "
try {
    $health = Invoke-RestMethod -Uri 'http://localhost:18789/health' -Method Get -ErrorAction Stop
    if ($health.ok) { 
        echo '✅ OpenClaw Gateway服务正常运行'
        echo '📍 访问地址: http://localhost:18789'
    } else {
        echo '❌ 服务返回异常状态'
    }
} catch {
    echo '❌ 服务健康检查失败: ' + $_.Exception.Message
}
"

echo.
echo ================================
echo 部署完成!
echo ================================
echo.
echo 下一步操作:
echo 1. 检查防火墙是否开放18789端口
echo 2. 配置需要同步的workspace文件
echo 3. 测试远程访问: http://[本机IP]:18789
echo.
pause