#!/bin/bash
# Ubuntu 装机脚本 - 用于 Android Termux 设备
# 目标设备: 10.35.204.243 (u0_a164)

echo "🎯 Ubuntu 装机脚本"
echo "================================"

# 检查设备连接
echo "🔍 检查设备连接..."
if ! ping -c 1 10.35.204.243 &>/dev/null; then
    echo "❌ 设备 10.35.204.243 离线"
    exit 1
fi

echo "✅ 设备在线"

# 检查 SSH 连接
echo "🔍 检查 SSH 服务..."
if ! nc -zv 10.35.204.243 8022 &>/dev/null; then
    echo "⚠️ SSH 服务未运行，需要手动启动设备上的 SSH"
    echo "请在设备上执行: sshd"
    exit 1
fi

echo "✅ SSH 服务正常"

# Ubuntu 安装函数
install_ubuntu() {
    echo "🚀 开始安装 Ubuntu..."
    
    # 通过 SSH 执行安装
    sshpass -p '123' ssh -p 8022 u0_a164@10.35.204.243 << 'EOF'
    echo "📦 更新包管理器..."
    pkg update -y
    
    echo "📦 安装 proot-distro..."
    pkg install proot-distro -y
    
    echo "🔍 查看可用发行版..."
    proot-distro list
    
    echo "🚀 安装 Ubuntu..."
    proot-distro install ubuntu
    
    echo "✅ 安装完成验证..."
    proot-distro list | grep ubuntu && echo "Ubuntu 安装成功!" || echo "Ubuntu 安装失败"
    
    echo "🎯 Ubuntu 使用方法:"
    echo "启动 Ubuntu: proot-distro login ubuntu"
    echo "退出 Ubuntu: exit"
EOF
}

# 执行安装
install_ubuntu

echo ""
echo "🎉 Ubuntu 装机脚本执行完成"
echo "📍 目标设备: 10.35.204.243"
echo "👤 用户名: u0_a164"
echo "🐧 系统: Ubuntu (proot)"
echo "================================"

# 验证安装
echo "🔍 验证安装结果..."
if sshpass -p '123' ssh -p 8022 u0_a164@10.35.204.243 "proot-distro list | grep -q ubuntu"; then
    echo "✅ Ubuntu 安装验证成功"
else
    echo "❌ Ubuntu 安装验证失败"
fi