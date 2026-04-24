#!/bin/bash
# 进程监控服务 - 定时检查异常进程

LOG_DIR="/root/.openclaw/workspace/logs/process_monitor"
mkdir -p "$LOG_DIR"

MONITOR_SCRIPT="/root/.openclaw/workspace/scripts/improved_process_monitor.sh"

# 监控函数
monitor_processes() {
    local timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
    local log_file="$LOG_DIR/monitor_$timestamp.log"
    
    echo "🕐 监控时间: $(date)" > "$log_file"
    echo "-"*50 >> "$log_file"
    
    # 运行监控
    $MONITOR_SCRIPT >> "$log_file" 2>&1
    
    # 检查是否有可疑进程
    if grep -q "🔴 发现" "$log_file"; then
        echo "🚨 警报: 发现可疑进程! 查看日志: $log_file"
        # 这里可以添加通知机制，比如发送邮件或消息
    else
        echo "✅ 系统正常 - $(date)"
    fi
}

# 立即运行一次
monitor_processes

echo ""
echo "🚀 进程监控系统已部署"
echo "📁 日志目录: $LOG_DIR"
echo "⏰ 建议设置定时任务: crontab -e"
echo "   添加: */5 * * * * $MONITOR_SCRIPT"
echo ""
echo "📋 当前系统进程概览:"
ps aux | wc -l | xargs echo "   总进程数:"
ps aux | grep -v grep | grep -E "(openclaw|adb|bash|proot)" | wc -l | xargs echo "   已知进程数:"