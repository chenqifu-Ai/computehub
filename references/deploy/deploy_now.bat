@echo off
chcp 65001 > nul

echo ==========================================
echo        OpenClaw 一键部署工具
echo ==========================================
echo 开始时间: %date% %time%
echo ==========================================
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

:: 部署函数
:run_step
echo 🚀 %*
%* > nul 2>&1
if errorlevel 1 (
    echo ❌ 执行失败
    exit /b 1
) else (
    echo ✅ 完成
)
echo.
goto :eof

:: 主部署流程
echo 🔍 步骤1/5: 检查Node.js
call :run_step node --version

if errorlevel 1 (
    echo ❌ Node.js未安装
    echo 💡 请从 https://nodejs.org 下载安装Node.js
    pause
    exit /b 1
)

echo 📦 步骤2/5: 安装OpenClaw
call :run_step npm install -g openclaw@latest

echo ⚙️  步骤3/5: 初始化配置
if not exist "%USERPROFILE%\.openclaw" mkdir "%USERPROFILE%\.openclaw"
call :run_step openclaw setup

echo 🚀 步骤4/5: 启动服务
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"

echo ⏳ 等待服务启动...
timeout /t 5 > nul

echo ✅ 步骤5/5: 验证部署
powershell -Command "
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:18789/health' -Method Get -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $health = $response.Content | ConvertFrom-Json
        if ($health.ok) {
            Write-Host '🎉 部署成功!' -ForegroundColor Green
            
            # 获取本机IP
            $ip = (Get-NetIPAddress | Where-Object { 
                $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*'
            } | Select-Object -First 1).IPAddress
            
            Write-Host '📍 本地访问: http://localhost:18789' -ForegroundColor Cyan
            Write-Host '🌐 远程访问: http://' + $ip + ':18789' -ForegroundColor Cyan
            Write-Host '📊 状态: ' + $health.status -ForegroundColor White
        }
    }
} catch {
    Write-Host '⚠️  服务验证失败，但部署已完成' -ForegroundColor Yellow
    Write-Host '💡 请手动检查服务状态' -ForegroundColor White
}
"

echo.
echo ==========================================
echo         部署完成!
echo ==========================================
echo.
echo 💡 下一步操作:
echo   • 检查防火墙设置
echo   • 测试远程访问
echo   • 配置所需技能
echo.
pause