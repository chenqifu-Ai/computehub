@echo off
chcp 65001 >nul 2>&1
setlocal

echo ========================================
echo  ComputeHub Worker 一键配置
echo ========================================
echo.

REM 配置参数
set BINARY=C:\Windows\System32\computehub.exe
set GW_URL=http://36.250.122.43:8282
set NODE_ID=Windows-mobile
set INTERVAL=3
set CONCURRENT=4
set HEARTBEAT=10

REM ---- 检查 binary 是否存在 ----
if not exist "%BINARY%" (
    echo [!] 错误: 找不到 %BINARY%
    echo     请先确认 computehub.exe 已部署到 System32
    pause
    exit /b 1
)
echo [OK] Binary 检查通过: %BINARY%

REM ---- 方法1: Startup 文件夹快捷方式 ----
echo [1/3] 创建 Startup 快捷方式...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
if not exist "%STARTUP%" (
    echo [!] 错误: 找不到 Startup 文件夹 %STARTUP%
    pause
    exit /b 1
)

echo set oWS = WScript.CreateObject("WScript.Shell") > %TEMP%\create_shortcut.vbs
echo sLinkFile = "%STARTUP%\ComputeHub Worker.lnk" >> %TEMP%\create_shortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %TEMP%\create_shortcut.vbs
echo oLink.TargetPath = "%BINARY%" >> %TEMP%\create_shortcut.vbs
echo oLink.Arguments = "worker --gw %GW_URL% --node-id %NODE_ID% --interval %INTERVAL% --concurrent %CONCURRENT% --heartbeat %HEARTBEAT%" >> %TEMP%\create_shortcut.vbs
echo oLink.WorkingDirectory = "C:\Windows\System32" >> %TEMP%\create_shortcut.vbs
echo oLink.Save() >> %TEMP%\create_shortcut.vbs
cscript //nologo %TEMP%\create_shortcut.vbs
del %TEMP%\create_shortcut.vbs
echo [OK] Startup 快捷方式已创建

REM ---- 方法2: 注册表 Run 项 ----
echo [2/3] 设置注册表启动项...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ComputeHubWorker" /t REG_SZ /d "\"%BINARY%\" worker --gw %GW_URL% --node-id %NODE_ID% --interval %INTERVAL% --concurrent %CONCURRENT% --heartbeat %HEARTBEAT%" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 注册表 HKCU\Run 已设置
) else (
    echo [!] 警告: 注册表设置失败（可能已有该条目）
)

REM ---- 方法3: 立即启动（不阻塞） ----
echo [3/3] 启动 Worker（新窗口）...
start "ComputeHub Worker" "%BINARY%" worker --gw %GW_URL% --node-id %NODE_ID% --interval %INTERVAL% --concurrent %CONCURRENT% --heartbeat %HEARTBEAT%

echo.
echo ========================================
echo  配置完成！
echo ========================================
echo.
echo  以下项目已设置:
echo    1. Startup 快捷方式: %STARTUP%\ComputeHub Worker.lnk
echo    2. 注册表 HKCU\Run: ComputeHubWorker
echo    3. Worker 已在独立窗口启动
echo.
echo  下次重启后会自动启动。
echo  按任意键关闭此窗口...
pause >nul
