#!/bin/bash
# 股票交易系统 - 简化启动脚本（无需安装依赖）

cd "$(dirname "$0")"

echo "================================================"
echo "📊 股票交易系统 - 量化交易平台"
echo "================================================"
echo ""
echo "✅ 使用Python标准库，无需安装任何依赖"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 创建数据目录
mkdir -p backend/data

# 启动服务
echo "🚀 启动API服务..."
cd backend
python3 simple_server.py