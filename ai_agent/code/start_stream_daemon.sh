#!/bin/bash
# Stream守护进程启动脚本

echo "🚀 启动Stream守护进程..."

# 检查是否已经在运行
if pgrep -f "stream_daemon.py" > /dev/null; then
    echo "✅ Stream守护进程已在运行"
    exit 0
fi

# 在后台启动守护进程
cd /root/.openclaw/workspace/ai_agent/code
nohup python3 stream_daemon.py > stream.log 2>&1 &

echo "✅ Stream守护进程已启动"
echo "📊 日志文件: /root/.openclaw/workspace/ai_agent/code/stream.log"
echo "🎯 目标: 公司永不停止，钱不白流"