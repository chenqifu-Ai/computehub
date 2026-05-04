@echo off
chcp 65001 > nul

echo ====================================
echo     OpenClaw服务管理器
echo ====================================
echo.

:menu
echo 请选择操作:
echo 1. 启动OpenClaw服务
echo 2. 停止OpenClaw服务  
echo 3. 重启OpenClaw服务
echo 4. 检查服务状态
echo 5. 退出
echo.
set /p choice=请输入选择 (1-5): 

echo.

if "%choice%"=="1" goto start_service
if "%choice%"=="2" goto stop_service
if "%choice%"=="3" goto restart_service
if "%choice%"=="4" goto check_status
if "%choice%"=="5" goto exit

echo ❌ 无效选择，请重新输入
echo.
goto menu

:start_service
echo 🚀 启动OpenClaw服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"
echo 等待服务启动...
timeout /t 3
echo ✅ 服务启动命令已发送
goto check_status

:stop_service
echo 🛑 停止OpenClaw服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul
echo ✅ 服务停止完成
goto menu

:restart_service
echo 🔄 重启OpenClaw服务...
call :stop_service
timeout /t 2
call :start_service
echo ✅ 服务重启完成
goto menu

:check_status
echo 🔍 检查服务状态...
powershell -Command "
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:18789/health' -Method Get -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $health = $response.Content | ConvertFrom-Json
        if ($health.ok) {
            Write-Host '✅ 服务状态: 正常运行' -ForegroundColor Green
            Write-Host '📊 状态信息: ' + $health.status -ForegroundColor White
        } else {
            Write-Host '❌ 服务状态: 异常' -ForegroundColor Red
        }
    } else {
        Write-Host ('❌ HTTP错误: ' + $response.StatusCode) -ForegroundColor Red
    }
} catch {
    if ($_.Exception.Message -like '*无法连接*') {
        Write-Host '❌ 服务状态: 未运行' -ForegroundColor Red
    } else {
        Write-Host ('❌ 检查错误: ' + $_.Exception.Message) -ForegroundColor Red
    }
}
"
echo.
goto menu

:exit
echo 👋 退出服务管理器
echo.
pause