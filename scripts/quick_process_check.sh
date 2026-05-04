#!/bin/bash
# 快速进程检查脚本

echo "🔍 快速进程检查"
echo "📊 检查时间: $(date)"
echo "-" * 40

# 快速检查高CPU进程
echo "高CPU进程:"
ps aux --sort=-%cpu | head -6 | awk '{printf "%-8s %-6s %-5s %s\n", $1, $2, $3, $11}'

echo ""
echo "系统负载: $(uptime | awk -F'load average:' '{print $2}')"
echo "总进程数: $(ps aux | wc -l)"
echo ""
echo "-" * 40
echo "✅ 快速检查完成"