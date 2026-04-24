#!/bin/bash
# OpenClaw Gateway修复启动脚本

echo "🔧 修复OpenClaw Gateway启动问题"
echo "📱 设备: 华为手机 (192.168.1.9)"
echo "⏰ 时间: $(date)"
echo "=========================================="

# 1. 停止现有服务
echo "🛑 停止现有Gateway服务..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "pkill -f 'openclaw-gateway' 2>/dev/null; pkill -f 'openclaw gateway' 2>/dev/null"

# 2. 等待进程停止
echo "⏳ 等待进程清理..."
sleep 3

# 3. 设置正确的绑定配置
echo "⚙️ 设置绑定地址为 0.0.0.0:18789..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "openclaw config set gateway.bind 0.0.0.0:18789 2>/dev/null || echo '使用命令行参数绑定'"

# 4. 启动Gateway服务
echo "🚀 启动Gateway服务..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "nohup openclaw gateway start --bind 0.0.0.0:18789 > ~/gateway_fixed.out 2> ~/gateway_fixed.err &"

# 5. 检查启动状态
echo "🔍 检查服务状态..."
sleep 5
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "ps aux | grep -E '(openclaw|gateway)' | grep -v grep; echo '检查端口监听...'; netstat -tlnp 2>/dev/null | grep :18789 || echo '端口检查中...'"

echo "=========================================="
echo "启动完成时间: $(date)"
echo "📋 日志文件: ~/gateway_fixed.out 和 ~/gateway_fixed.err"