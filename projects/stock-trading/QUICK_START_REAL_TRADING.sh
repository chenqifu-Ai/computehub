#!/bin/bash
# 实盘交易快速启动脚本

echo "======================================"
echo "🚀 股票交易系统 - 实盘启动脚本"
echo "======================================"

# 1. 检查服务
echo ""
echo "📊 检查服务状态..."
if curl -s http://localhost:8000/api/market/stocks > /dev/null; then
    echo "✅ 后端服务运行中"
else
    echo "⚠️  后端服务未运行，正在启动..."
    cd /root/.openclaw/workspace/projects/stock-trading/backend
    nohup python3 simple_server.py > /tmp/stock-server.log 2>&1 &
    sleep 3
    echo "✅ 后端服务已启动"
fi

# 2. 检查券商配置
echo ""
echo "📋 检查券商配置..."
cat /root/.openclaw/workspace/projects/stock-trading/backend/config/brokers/default.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"默认券商：{d['default_broker']}\")"

# 3. 测试连接
echo ""
echo "🧪 测试系统连接..."
python3 /root/.openclaw/workspace/projects/stock-trading/test_real_trading.py

echo ""
echo "======================================"
echo "✅ 启动完成！"
echo "======================================"
