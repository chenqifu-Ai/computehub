#!/bin/bash
# 股票交易系统启动脚本

cd "$(dirname "$0")"

echo "🚀 启动股票交易系统..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 安装依赖
if [ -f "requirements.txt" ]; then
    echo "📦 安装依赖..."
    pip install -r requirements.txt -q 2>/dev/null || pip3 install -r requirements.txt -q 2>/dev/null
fi

# 创建数据目录
mkdir -p data

# 启动服务
echo "🌐 启动API服务..."
echo "📍 API地址: http://localhost:8000"
echo "📖 API文档: http://localhost:8000/docs"
echo ""
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload