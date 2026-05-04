#!/bin/bash
# SSH连接华为手机脚本 (标准连接模式)
# 设备: 华为手机 (HWI-AL00)
# 用户名: u0_a46
# 密码: 123
# SSH端口: 8022
# 连接模式: ssh → proot-distro login ubuntu

# 使用方法: ./connect_huawei.sh <IP地址>

if [ -z "$1" ]; then
    echo "使用方法: $0 <IP地址>"
    echo "示例: $0 10.35.204.26"
    echo "当前已知IP: 10.35.204.26 (动态变化)"
    exit 1
fi

IP_ADDRESS="$1"

echo "🔌 华为手机标准连接模式"
echo "📱 设备: 华为手机 (HWI-AL00)"
echo "👤 用户名: u0_a46"
echo "🔑 密码: 123"
echo "🌐 IP地址: $IP_ADDRESS"
echo "🚪 端口: 8022"
echo ""
echo "连接步骤:"
echo "1. SSH连接: ssh -p 8022 u0_a46@$IP_ADDRESS"
echo "2. 输入密码: 123"
echo "3. 进入Ubuntu: proot-distro login ubuntu"
echo "4. 退出: exit (Ubuntu) → exit (SSH)"
echo ""
echo "正在连接..."

# SSH连接命令
ssh -p 8022 u0_a46@$IP_ADDRESS