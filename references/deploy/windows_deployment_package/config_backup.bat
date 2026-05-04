@echo off
chcp 65001 > nul

echo ====================================
echo     OpenClaw配置备份工具
echo ====================================
echo.

:: 创建备份目录
set BACKUP_DIR=%USERPROFILE%\OpenClaw_Backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: 生成时间戳
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set datetime=%%a
set timestamp=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2%_%datetime:~8,2%-%datetime:~10,2%-%datetime:~12,2%

:: 备份文件路径
set BACKUP_FILE=%BACKUP_DIR%\openclaw_backup_%timestamp%.zip

echo 正在备份OpenClaw配置...
echo 源目录: %USERPROFILE%\.openclaw
echo 备份文件: %BACKUP_FILE%
echo.

:: 检查源目录是否存在
if not exist "%USERPROFILE%\.openclaw" (
    echo ❌ 源目录不存在: %USERPROFILE%\.openclaw
    echo 💡 请先运行 openclaw setup 初始化配置
    pause
    exit /b 1
)

:: 使用PowerShell创建ZIP备份
powershell -Command "
$ErrorActionPreference = 'Stop'
try {
    Write-Host '创建配置备份...' -ForegroundColor Yellow
    
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    
    $source = '%USERPROFILE%\.openclaw'
    $destination = '%BACKUP_FILE%'
    
    # 删除已存在的备份文件
    if (Test-Path $destination) {
        Remove-Item $destination -Force
    }
    
    # 创建ZIP备份
    [System.IO.Compression.ZipFile]::CreateFromDirectory($source, $destination)
    
    # 计算备份大小
    $size = (Get-Item $destination).Length
    $sizeMB = [math]::Round($size / 1MB, 2)
    
    Write-Host '✅ 备份完成!' -ForegroundColor Green
    Write-Host '📁 备份文件: ' + $destination -ForegroundColor Cyan
    Write-Host '💾 文件大小: ' + $sizeMB + ' MB' -ForegroundColor Cyan
    
    # 显示备份内容
    $zip = [System.IO.Compression.ZipFile]::OpenRead($destination)
    $fileCount = $zip.Entries.Count
    $zip.Dispose()
    
    Write-Host '📊 文件数量: ' + $fileCount -ForegroundColor White
    
} catch {
    Write-Host '❌ 备份失败: ' + $_.Exception.Message -ForegroundColor Red
    exit 1
}
"

if errorlevel 1 (
    echo ❌ 备份过程出错
    pause
    exit /b 1
)

echo.
echo ====================================
echo     备份操作完成!
echo ====================================
echo.
echo 💡 备份信息:
echo   位置: %BACKUP_DIR%
echo   文件: openclaw_backup_%timestamp%.zip
echo.
echo 🎯 恢复说明:
echo   如需恢复配置，请:
echo   1. 停止OpenClaw服务
echo   2. 删除现有配置目录
echo   3. 解压备份文件到 %USERPROFILE%\.openclaw
echo   4. 重启服务
echo.
pause