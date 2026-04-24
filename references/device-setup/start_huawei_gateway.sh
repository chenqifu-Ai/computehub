#!/bin/bash
# 华为设备 OpenClaw Gateway 启动脚本
# 绕过 Android 服务安装检查

# SSH 连接到华为设备并启动网关
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 << 'EOF'
cd ~

# 停止任何可能运行的网关进程
pkill -f "openclaw.*gateway" || true
pkill -f "node.*gateway" || true
sleep 2

# 检查端口是否被占用
if netstat -tln | grep -q ":18789"; then
    echo "端口 18789 已被占用，尝试释放..."
    fuser -k 18789/tcp || true
    sleep 2
fi

# 尝试直接启动网关（绕过服务检查）
echo "尝试启动 OpenClaw Gateway..."

# 方法1: 使用 nohup 后台启动
nohup openclaw gateway start --bind 0.0.0.0 > gateway_direct.out 2> gateway_direct.err &

# 等待几秒后检查状态
sleep 5

# 检查进程是否运行
if ps aux | grep -q "[o]penclaw.*gateway"; then
    echo "✅ OpenClaw Gateway 启动成功"
    echo "监听地址: ws://192.168.1.9:18789"
    echo "Token: 146aaa219c512bd2495e24d4ffb0c6f1422e5767be997351"
else
    echo "❌ OpenClaw Gateway 启动失败"
    echo "错误日志:"
    cat gateway_direct.err | tail -10
fi

# 显示端口状态
netstat -tln | grep 18789 || echo "端口 18789 未监听"

EOF

echo "启动脚本执行完成"