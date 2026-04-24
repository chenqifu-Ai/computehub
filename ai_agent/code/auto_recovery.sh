#!/bin/bash
# 🔴 CEO自动恢复脚本
# 在系统异常时自动执行

echo "[{date '+%H:%M:%S'}] 🔧 CEO自动恢复启动..."

# 清理高CPU进程
echo "  清理僵尸进程..."
killall -9 python 2>/dev/null
sleep 1

# 检查OpenClaw
if ! pgrep -f "openclaw" > /dev/null; then
    echo "  重启OpenClaw Gateway..."
    openclaw gateway restart 2>&1 &
fi

echo "[{date '+%H:%M:%S'}] ✅ 自动恢复完成"
