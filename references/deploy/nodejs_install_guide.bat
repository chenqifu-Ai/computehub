@echo off
chcp 65001 > nul

echo ==========================================
echo         Node.js 安装指南
echo ==========================================
echo.

echo ❌ 检测到Node.js未安装
echo 💡 请按照以下步骤安装Node.js
echo.

echo 🚀 安装步骤:
echo 1. 访问Node.js官方网站:
echo    https://nodejs.org
echo.
echo 2. 下载Windows安装包:
echo    • 推荐版本: Node.js 20.11.1 LTS
echo    • 直接下载: https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi
echo.
echo 3. 运行安装程序:
echo    • 双击下载的.msi文件
echo    • 选择默认安装选项
echo    • 完成安装
echo.
echo 4. 验证安装:
echo    • 打开新的命令提示符
echo    • 运行: node --version
echo    • 应该显示: v20.11.1
echo.
echo 5. 安装完成后，重新运行OpenClaw部署
echo.
echo 📝 快速安装命令 (PowerShell):
echo powershell -Command "
echo    $url = 'https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi'
echo    $output = '$env:TEMP\\nodejs.msi'
echo    Invoke-WebRequest -Uri $url -OutFile $output
echo    Start-Process msiexec -ArgumentList '/i \"$output\" /quiet /norestart' -Wait
echo    echo 'Node.js安装完成'
echo "
echo.
echo ==========================================
echo   安装完成后重新运行部署命令
echo ==========================================
pause