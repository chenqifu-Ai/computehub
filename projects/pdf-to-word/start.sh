#!/bin/bash
# PDF转Word工具启动脚本

cd "$(dirname "$0")"

echo "================================================"
echo "📄 PDF转Word工具"
echo "================================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 启动Web服务
echo "🌐 启动Web服务..."
echo "📍 访问地址: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "================================================"
echo ""

python3 pdf2word.py --web