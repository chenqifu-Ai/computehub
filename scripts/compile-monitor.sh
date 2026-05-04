#!/bin/bash

# 🎯 编译实时监控脚本

echo "🚀 开始编译实时监控 (Ctrl+C 停止)"
echo "📊 监控频率: 每10秒更新"
echo "---"

while true; do
    # 获取当前时间
    timestamp=$(date '+%H:%M:%S')
    
    # 检查编译进程
    compile_pids=$(ps aux | grep -E '(node.*tsc|pnpm.*build)' | grep -v grep | awk '{print $2}' | tr '\n' ' ')
    
    if [ -z "$compile_pids" ]; then
        echo "⏰ [$timestamp] ❌ 无编译进程 - 编译可能已完成或失败"
    else
        echo "⏰ [$timestamp] ✅ 编译进行中"
        
        # 显示每个编译进程状态
        for pid in $compile_pids; do
            process_info=$(ps -p $pid -o pid,pcpu,pmem,etime,comm 2>/dev/null | tail -1)
            if [ -n "$process_info" ]; then
                echo "   📊 $process_info"
            fi
        done
        
        # 显示CPU和内存总体使用
        cpu_mem=$(ps aux | grep -E '(node.*tsc|pnpm.*build)' | grep -v grep | awk '{cpu+=$3; mem+=$4} END {print "💻 CPU:" cpu "% MEM:" mem "MB"}')
        echo "   $cpu_mem"
    fi
    
    echo "---"
    sleep 10
done