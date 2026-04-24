#!/bin/bash
# OpenClaw Gateway基础启动脚本

# 停止现有服务
pkill -f "openclaw-gateway" 2>/dev/null
pkill -f "openclaw gateway" 2>/dev/null
sleep 2

# 启动Gateway服务
echo "🚀 启动OpenClaw Gateway..."
nohup openclaw gateway start --bind auto > ~/gateway.out 2> ~/gateway.err &

# 检查状态
echo "⏳ 等待服务启动..."
sleep 5

# 验证启动
echo "🔍 检查服务状态:"
ps aux | grep -E "(openclaw|gateway)" | grep -v grep
echo "🌐 检查端口监听:"
netstat -tlnp 2>/dev/null | grep :18789 || echo "端口检查中..."

echo "✅ 启动命令执行完成!"
echo "📋 日志文件: ~/gateway.out 和 ~/gateway.err"
