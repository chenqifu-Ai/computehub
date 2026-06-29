@echo off
chcp 65001 >nul
title Installing Node.js + OpenClaw...
echo ========================================
echo   Node.js + OpenClaw 一键安装脚本
echo ========================================
echo.

:: Step 1: Check if already installed
if exist "C:\Program Files\nodejs\node.exe" (
    "C:\Program Files\nodejs\node.exe" --version
    echo Node.js already installed, skipping...
    goto :install_openclaw
)

:: Step 2: Download Node.js MSI from Gateway (local network)
echo [1/3] Downloading Node.js MSI...
mkdir C:\installers 2>nul
bitsadmin /transfer njs /download /priority high http://36.250.122.43:8282/api/v1/files/node-v24.16.0-x64.msi C:\installers\node.msi
if %errorlevel% neq 0 (
    echo bitsadmin failed, trying certutil...
    certutil -urlcache -split -f http://36.250.122.43:8282/api/v1/files/node-v24.16.0-x64.msi C:\installers\node.msi
)
if not exist C:\installers\node.msi (
    echo Download failed! Trying alternate port 8999...
    bitsadmin /transfer njs2 /download /priority high http://36.250.122.43:8999/nodejs.zip C:\installers\nodejs.zip
    if exist C:\installers\nodejs.zip (
        echo Extracting zip...
        powershell -Command "Expand-Archive -Path C:\installers\nodejs.zip -DestinationPath C:\installers\node-extracted -Force; $dir=Get-ChildItem C:\installers\node-extracted -Directory ^| Select -First 1; if ($dir) { Copy-Item \"$($dir.FullName)\*\" \"C:\Program Files\nodejs\" -Recurse -Force }"
        goto :verify_node
    ) else (
        echo ALL DOWNLOAD METHODS FAILED
        echo.
        echo Please manually download from:
        echo   http://36.250.122.43:8282/api/v1/files/node-v24.16.0-x64.msi
        echo.
        pause
        exit /b 1
    )
)

:: Step 3: Install Node.js MSI
echo [2/3] Installing Node.js MSI (this takes a moment)...
msiexec /i C:\installers\node.msi /qn /norestart /passive
echo Waiting for installation to complete...
ping -n 10 127.0.0.1 >nul

:verify_node
echo [2/3 - verify] Checking Node.js...
if exist "C:\Program Files\nodejs\node.exe" (
    "C:\Program Files\nodejs\node.exe" --version
) else (
    echo Node.js not found at C:\Program Files\nodejs
    echo Trying C:\Program Files (x86)\nodejs...
    if exist "C:\Program Files (x86)\nodejs\node.exe" (
        "C:\Program Files (x86)\nodejs\node.exe" --version
    ) else (
        echo FAILED: node.exe not found after installation
        pause
        exit /b 1
    )
)

:install_openclaw
echo [3/3] Installing OpenClaw...
"C:\Program Files\nodejs\npm.cmd" install -g openclaw@2026.3.13
if %errorlevel% neq 0 (
    echo Trying latest version...
    "C:\Program Files\nodejs\npm.cmd" install -g openclaw
)

echo.
echo ====== VERIFICATION ======
echo Node.js: 
if exist "C:\Program Files\nodejs\node.exe" (
    "C:\Program Files\nodejs\node.exe" --version
)
echo npm:
if exist "C:\Program Files\nodejs\npm.cmd" (
    "C:\Program Files\nodejs\npm.cmd" --version
)
echo OpenClaw:
if exist "C:\Program Files\nodejs\openclaw.cmd" (
    "C:\Program Files\nodejs\openclaw.cmd" --version
)
echo.
echo ====== DONE ======
echo You can now run: openclaw
pause