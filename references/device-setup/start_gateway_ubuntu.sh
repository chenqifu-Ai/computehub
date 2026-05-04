#!/bin/bash
# OpenClaw Gateway Ubuntu环境启动脚本

# 进入Ubuntu环境启动
echo "🐧 在Ubuntu环境中启动Gateway..."
proot-distro login ubuntu -- bash -c \"
    # 停止现有服务
    pkill -f 'openclaw-gateway' 2>/dev/null
    pkill -f 'openclaw gateway' 2>/dev/null
    sleep 2
    
    # 启动服务
    echo '🚀 启动OpenClaw Gateway...'
    nohup openclaw gateway start --bind auto > /tmp/gateway-ubuntu.out 2> /tmp/gateway-ubuntu.err &
    
    # 检查状态
    sleep 3
    echo '🔍 服务状态:'
    ps aux | grep -E '(openclaw|gateway)' | grep -v grep | head -3
    echo '🌐 端口监听:'
    netstat -tlnp 2>/dev/null | grep :18789 || echo '端口检查中...'
    
    echo '✅ Ubuntu环境启动完成!'
    echo '📋 日志: /tmp/gateway-ubuntu.out 和 /tmp/gateway-ubuntu.err'
\"
