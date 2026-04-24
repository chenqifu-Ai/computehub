#!/bin/bash

# OpenClaw Gateway启动脚本
# 用法: ./start_gateway.sh [端口号]

PORT="${1:-18789}"

echo "🚀 启动OpenClaw Gateway..."
echo "端口: $PORT"
echo "绑定模式: lan"

# 检查OpenClaw是否安装
if ! command -v openclaw >/dev/null 2>&1; then
    echo "❌ OpenClaw未安装"
    exit 1
fi

# 启动Gateway
echo "📡 启动Gateway服务..."
openclaw gateway run --bind lan --port "$PORT"

echo "✅ Gateway启动完成"