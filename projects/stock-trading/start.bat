# 股票交易软件 - Windows启动脚本

@echo off
chcp 65001 >nul
echo =====================================
echo   股票交易软件 - 一键启动
echo =====================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未安装Python，请先安装Python3
    pause
    exit /b 1
)

echo ✅ Python已安装

REM 安装依赖
echo.
echo 📦 安装依赖...
pip install -q fastapi uvicorn pyjwt pandas requests akshare 2>nul

REM 创建数据目录
if not exist "backend\data" mkdir backend\data

echo.
echo 🚀 启动服务...
echo.
echo =====================================
echo   访问地址
echo =====================================
echo   后端API: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo   前端页面: 请用浏览器打开 frontend\index.html
echo =====================================
echo.

cd backend
python main.py

pause