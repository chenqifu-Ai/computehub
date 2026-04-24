#!/bin/bash
# 集合竞价数据提醒
# 09:15 运行

echo "========================================"
echo "📊 集合竞价数据提醒"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

cd /root/.openclaw/workspace
python3 ai_agent/code/call_auction.py

echo ""
echo "✅ 分析完成"