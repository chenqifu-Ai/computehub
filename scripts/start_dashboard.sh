#!/bin/bash
# 启动进程监控驾驶舱

echo "🚀 启动进程监控驾驶舱..."
echo "📊 访问地址: http://localhost:8080"
echo "🔄 自动刷新: 每30秒"
echo "⏹️  停止: Ctrl+C"
echo ""

cd /root/.openclaw/workspace/scripts
python3 process_monitor_dashboard.py