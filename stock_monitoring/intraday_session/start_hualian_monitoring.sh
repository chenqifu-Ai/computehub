#!/bin/bash
# 华联股份监控启动脚本

echo "启动华联股份紧急监控系统..."
echo "监控频率: 每5分钟一次"
echo "止损价位: ¥1.60"
echo "当前时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 无限循环，每5分钟监控一次
while true; do
    echo "=================================================="
    echo "执行华联股份监控 - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=================================================="
    
    # 执行监控脚本
    cd /root/.openclaw/workspace
    python3 stock_monitoring/intraday_session/hualian_monitor.py
    
    echo ""
    echo "等待5分钟..."
    echo ""
    
    # 等待5分钟
    sleep 300

done