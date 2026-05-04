# 股票交易软件 - 快速启动脚本

echo "====================================="
echo "  股票交易软件 - 启动中..."
echo "====================================="
echo ""

# 检查Python版本
echo "📌 检查Python版本..."
python3 --version

# 安装依赖
echo ""
echo "📦 安装依赖..."
pip install fastapi uvicorn pyjwt pandas requests akshare -q 2>/dev/null

# 创建数据目录
mkdir -p data

# 启动后端
echo ""
echo "🚀 启动后端服务..."
echo ""
echo "====================================="
echo "  服务地址"
echo "====================================="
echo "  API文档: http://localhost:8000/docs"
echo "  前端页面: 请用浏览器打开 frontend/index.html"
echo "====================================="
echo ""

python3 main.py