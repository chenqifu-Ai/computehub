#!/bin/bash
# 简单性能监控脚本

echo "🔍 系统性能监控"
echo "📊 检查时间: $(date)"
echo "-" * 50

# 获取系统负载
load_avg=$(cat /proc/loadavg 2>/dev/null | awk '{print $1" "$2" "$3}' || echo "未知")
echo "📈 系统负载: $load_avg"

# 获取CPU核心数
cpu_cores=$(nproc 2>/dev/null || echo "未知")
echo "📊 CPU核心: $cpu_cores"

# 检查高CPU进程
echo ""
echo "🔍 高CPU进程检查:"
echo "-" * 30
ps aux --sort=-%cpu | head -10 | awk 'NR==1 {print "   " $0}; NR>1 {if ($3 > 5.0) print "⚠️  " $0}' | head -6

# 检查长时间运行的高CPU进程
echo ""
echo "🔍 长时间运行进程检查:"
echo "-" * 30
ps -eo pid,user,%cpu,etime,comm --sort=-etime | head -10 | awk 'NR==1 {print "   " $0}; NR>1 {if ($3 > 2.0) print "⏰  " $0}' | head -6

# 内存使用情况
echo ""
echo "🔍 内存使用情况:"
echo "-" * 30
free -h

echo ""
echo "-" * 50
echo "🕐 检查完成: $(date)"