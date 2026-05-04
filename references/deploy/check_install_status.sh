#!/bin/bash
# OpenClaw安装状态检查脚本

echo "🔍 检查华为手机OpenClaw安装状态..."
echo "📱 设备: 192.168.1.9 (华为手机)"
echo "⏰ 时间: $(date)"
echo "=========================================="

# 检查网络连通性
if ping -c 2 192.168.1.9 >/dev/null 2>&1; then
    echo "✅ 网络连接正常"
else
    echo "❌ 网络连接失败"
    exit 1
fi

# 检查SSH连接
echo "尝试SSH连接检查..."
if timeout 15 sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no -o ConnectTimeout=10 u0_a46@192.168.1.9 "echo 'SSH连接成功'" 2>/dev/null; then
    echo "✅ SSH连接正常"
    
    # 检查Ubuntu环境
    echo "检查Ubuntu环境..."
    sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
        "proot-distro list 2>/dev/null | grep ubuntu || echo 'Ubuntu未安装'"
    
    # 检查OpenClaw安装
    echo "检查OpenClaw安装..."
    sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
        "proot-distro login ubuntu -- which openclaw 2>/dev/null && echo '✅ OpenClaw已安装' || echo '❌ OpenClaw未安装'"
    
else
    echo "❌ SSH连接失败或超时"
fi

echo "=========================================="
echo "检查完成时间: $(date)"