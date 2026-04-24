#!/bin/bash

# 华为手机OpenClaw Gateway启动脚本
# 专门为华为手机优化配置
# 用法: ./start_huawei_gateway.sh

echo "🚀 启动华为手机OpenClaw Gateway..."
echo "设备: 华为手机 (u0_a46@192.168.1.9)"
echo "端口: 18789"
echo "绑定模式: lan"

# 检查OpenClaw是否安装
if ! command -v openclaw >/dev/null 2>&1; then
    echo "❌ OpenClaw未安装，请先安装OpenClaw"
    exit 1
fi

# 检查配置文件
if [ ! -f ~/.openclaw/openclaw.json ]; then
    echo "⚠️  配置文件不存在，使用默认配置"
    openclaw config init
fi

# 设置优化配置（针对华为手机）
echo "📋 设置华为手机优化配置..."
openclaw config set gateway.controlUi.dangerouslyAllowHostHeaderOriginFallback true
openclaw config set gateway.remote.url http://192.168.1.17:18789
openclaw config set gateway.bind lan

# 启动Gateway（跳过UI依赖检查）
echo "📡 启动Gateway服务（跳过UI检查）..."
openclaw gateway run --bind lan --port 18789 --cli-backend-logs

echo "✅ 华为手机Gateway启动完成"
echo "📊 访问地址: http://192.168.1.9:18789"
echo "🔗 Gateway: ws://192.168.1.9:18789"