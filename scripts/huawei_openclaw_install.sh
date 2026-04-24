#!/bin/bash
# 华为手机OpenClaw安装脚本

echo "📱 开始华为手机OpenClaw安装流程"
echo "================================"

# 设备信息
HUAWEI_IP="192.168.1.9"
HUAWEI_USER="u0_a46"
HUAWEI_PASSWORD="123"
SSH_PORT="8022"

# 检查连接
echo "🔍 检查设备连接..."
if ping -c 2 $HUAWEI_IP >/dev/null 2>&1; then
    echo "✅ 设备在线: $HUAWEI_IP"
else
    echo "❌ 设备离线，请检查网络连接"
    exit 1
fi

# 检查SSH连接
echo "🔌 测试SSH连接..."
if sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "echo 'SSH连接成功'"; then
    echo "✅ SSH连接正常"
else
    echo "❌ SSH连接失败"
    exit 1
fi

# 检查环境
echo "🔧 检查系统环境..."
sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
    echo 'Node.js版本:' && node --version
    echo 'npm版本:' && npm --version
    echo '当前目录:' && pwd
    echo 'OpenClaw目录状态:' && ls -la ~/openclaw/ 2>/dev/null | head -3 || echo 'OpenClaw目录不存在'
"

# 检查OpenClaw是否已安装
echo "📦 检查OpenClaw安装状态..."
INSTALLED=$(sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
    if [ -f ~/openclaw/dist/cli.js ]; then
        echo 'installed'
    else
        echo 'not_installed'
    fi
")

if [ "$INSTALLED" = "installed" ]; then
    echo "✅ OpenClaw已安装"
    
    # 尝试启动OpenClaw
    echo "🚀 尝试启动OpenClaw..."
    sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
        cd ~/openclaw
        echo '启动Gateway...'
        nohup node dist/cli.js gateway > gateway.log 2> gateway.err &
        sleep 3
        echo '检查进程:' && ps aux | grep node | grep -v grep || echo '未找到进程'
    "
else
    echo "🔧 OpenClaw需要安装或构建"
    
    # 安装依赖
    echo "📦 安装依赖..."
    sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
        cd ~/openclaw
        echo '安装npm依赖...'
        npm install 2>&1 | tail -10
    "
    
    # 构建OpenClaw
    echo "🔨 构建OpenClaw..."
    sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $极AWEI_USER@$HUAWEI_IP "
        cd ~/openclaw
        echo '开始构建...'
        npm run build 2> build_error.log | head -20
        echo '构建完成，检查文件:' && ls -la dist/ 2>/dev/null | head -5 || echo '构建失败'
    "
fi

# 检查最终状态
echo "📊 最终状态检查..."
sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP "
    echo '=== 系统状态 ==='
    echo '内存使用:' && free -m | head -2
    echo '磁盘空间:' && df -h /data
    echo '=== OpenClaw状态 ==='
    if [ -f ~/openclaw/dist/cli.js ]; then
        echo '✅ OpenClaw构建成功'
        echo '文件大小:' && du -sh ~/openclaw/dist/
    else
        echo '❌ OpenClaw构建失败'
        echo '错误日志:' && tail -10 ~/openclaw/build_error.log 2>/dev/null || echo '无错误日志'
    fi
"

echo ""
echo "🎉 华为手机OpenClaw安装流程完成"
echo "📋 下一步操作:"
echo "   1. 访问 http://$HUAWEI_IP:18789 检查Gateway"
echo "   2. 查看日志: ssh -p $SSH_PORT $HUAWEI_USER@$HUAWEI_IP 'tail -f ~/openclaw/gateway.log'"
echo "   3. 配置连接: 使用token 2159c9affb69a78acdef02bc0e0c68824bedcc8ccf11bc5b"