#!/bin/bash
# OpenClaw Gateway启动脚本集合

echo "🚀 OpenClaw Gateway启动脚本"
echo "📱 设备: 192.168.1.9 (华为手机)"
echo "🐧 环境: Termux + Ubuntu Proot"
echo "=========================================="

# 脚本1: 基础启动脚本
echo "1️⃣ 基础启动脚本 (start_gateway_basic.sh)"
cat > /root/.openclaw/workspace/start_gateway_basic.sh << 'EOF'
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
EOF

# 脚本2: Ubuntu环境启动脚本
echo "2️⃣ Ubuntu环境启动脚本 (start_gateway_ubuntu.sh)"
cat > /root/.openclaw/workspace/start_gateway_ubuntu.sh << 'EOF'
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
EOF

# 脚本3: 高级管理脚本
echo "3️⃣ 高级管理脚本 (gateway_manager.sh)"
cat > /root/.openclaw/workspace/gateway_manager.sh << 'EOF'
#!/bin/bash
# OpenClaw Gateway高级管理脚本

case "$1" in
    start)
        echo "🚀 启动Gateway服务..."
        nohup openclaw gateway start --bind auto > ~/gateway.out 2> ~/gateway.err &
        echo "✅ 启动命令已发送"
        ;;
    stop)
        echo "🛑 停止Gateway服务..."
        pkill -f "openclaw-gateway"
        pkill -f "openclaw gateway"
        echo "✅ 服务已停止"
        ;;
    restart)
        echo "🔄 重启Gateway服务..."
        pkill -f "openclaw-gateway"
        pkill -f "openclaw gateway"
        sleep 2
        nohup openclaw gateway start --bind auto > ~/gateway.out 2> ~/gateway.err &
        echo "✅ 重启完成"
        ;;
    status)
        echo "🔍 Gateway服务状态:"
        ps aux | grep -E "(openclaw|gateway)" | grep -v grep
        echo "🌐 网络状态:"
        netstat -tlnp 2>/dev/null | grep :18789 || echo "端口未监听"
        ;;
    logs)
        echo "📋 Gateway日志:"
        tail -20 ~/gateway.out 2>/dev/null || echo "无输出日志"
        echo "❌ 错误日志:"
        tail -20 ~/gateway.err 2>/dev/null || echo "无错误日志"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo "   start    - 启动Gateway服务"
        echo "   stop     - 停止Gateway服务"
        echo "   restart  - 重启Gateway服务"
        echo "   status   - 查看服务状态"
        echo "   logs     - 查看日志"
        ;;
esac
EOF

# 设置执行权限
chmod +x /root/.openclaw/workspace/start_gateway_basic.sh
chmod +x /root/.openclaw/workspace/start_gateway_ubuntu.sh
chmod +x /root/.openclaw/workspace/gateway_manager.sh

echo "=========================================="
echo "✅ 启动脚本创建完成!"
echo "📁 脚本位置: /root/.openclaw/workspace/"
echo ""
echo "🚀 使用方式:"
echo "   ./start_gateway_basic.sh    - 基础启动"
echo "   ./start_gateway_ubuntu.sh   - Ubuntu环境启动"
echo "   ./gateway_manager.sh [cmd]  - 高级管理"
echo ""
echo "🎯 推荐使用: ./gateway_manager.sh start"