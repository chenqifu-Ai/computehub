#!/bin/bash
# 简化版华为手机OpenClaw安装

echo "📱 简化版华为手机OpenClaw安装"
echo "=============================="

HUAWEI_IP="192.168.1.9"
HUAWEI_USER="u0_a46"
HUAWEI_PASSWORD="123"
SSH_PORT="8022"

# 检查连接
echo "🔍 检查设备连接..."
ping -c 2 $HUAWEI_IP >/dev/null 2>&1 && echo "✅ 设备在线" || echo "❌ 设备离线"

# 方法1: 使用npm直接安装OpenClaw
echo "📦 方法1: 使用npm全局安装OpenClaw"
sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
    echo '安装OpenClaw...'
    npm install -g openclaw@latest 2>&1
    echo '安装完成，检查版本:'
    openclaw --version 2>/dev/null || echo 'OpenClaw命令不可用'
"

# 方法2: 如果方法1失败，使用现有目录
echo "🔧 方法2: 使用现有OpenClaw目录"
sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
    cd ~/openclaw
    echo '当前目录: ' && pwd
    echo '尝试直接启动Gateway...'
    npx openclaw gateway &
    sleep 5
    echo '检查进程:' && ps aux | grep -E '(node|openclaw)' | grep -v grep || echo '未找到进程'
"

# 检查Gateway状态
echo "🌐 检查Gateway状态..."
sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
    echo '检查端口18789:'
    netstat -tlnp 2>/dev/null | grep :18789 || echo '端口未监听'
    echo '检查Gateway日志:'
    ls -la ~/openclaw/gateway.log 2>/dev/null && tail -5 ~/openclaw/gateway.log || echo '无日志文件'
"

echo ""
echo "🎯 安装完成"
echo "📋 访问地址: http://$HUAWEI_IP:18789"
echo "🔑 连接Token: 2159c9affb69a78acdef02bc0e0c68824bedcc8ccf11bc5b"