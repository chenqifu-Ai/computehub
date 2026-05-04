#!/bin/bash
# 华联股份监控手动执行脚本

echo "📊 执行华联股份持仓监控..."
cd /root/.openclaw/workspace
python3 ai_agent/code/stock_monitor_000882.py

echo ""
echo "✅ 监控完成"
