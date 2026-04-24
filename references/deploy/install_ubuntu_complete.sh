#!/bin/bash
# 完整的 Ubuntu 装机脚本
# 目标: 10.35.204.243, 用户: u0_a165, 密码: 123

echo "🎯 Ubuntu 装机脚本 - 完整版"
echo "================================"

# 清理 SSH 主机密钥
echo "🔧 清理 SSH 主机密钥..."
ssh-keygen -R "[10.35.204.243]:8022" 2>/dev/null
ssh-keyscan -p 8022 10.35.204.243 2>/dev/null >> ~/.ssh/known_hosts

echo "✅ SSH 配置完成"

# 安装函数
install_ubuntu() {
    echo "🚀 开始安装 Ubuntu..."
    
    # 通过 SSH 执行完整安装
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a165@10.35.204.243 << 'EOF'
    
    echo "📦 步骤 1: 更新包管理器"
    pkg update -y
    
    echo "📦 步骤 2: 安装 proot-distro"
    pkg install proot-distro -y
    
    echo "🔍 步骤 3: 查看可用发行版"
    proot-distro list
    
    echo "🚀 步骤 4: 安装 Ubuntu"
    proot-distro install ubuntu
    
    echo "✅ 步骤 5: 验证安装"
    if proot-distro list | grep -q ubuntu; then
        echo "🎉 Ubuntu 安装成功!"
        echo ""
        echo "🐧 Ubuntu 使用指南:"
        echo "启动: proot-distro login ubuntu"
        echo "退出: exit"
        echo "更新: apt update && apt upgrade"
        echo "安装软件: apt install <package-name>"
    else
        echo "❌ Ubuntu 安装失败"
        echo "尝试手动安装..."
        pkg install proot-distro -y
        proot-distro install ubuntu
        proot-distro list | grep -q ubuntu && echo "✅ 手动安装成功" || echo "❌ 手动安装失败"
    fi
EOF
}

# 执行安装
install_ubuntu

echo ""
echo "🎯 装机结果总结:"
echo "📍 目标设备: 10.35.204.243"
echo "👤 用户名: u0_a165"
echo "🔑 密码: 123"
echo "🐧 系统: Ubuntu (proot)"
echo "📁 安装位置: /data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu/"
echo "================================"

# 最终验证
echo "🔍 最终验证..."
if sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 "proot-distro list | grep -q ubuntu"; then
    echo "✅ Ubuntu 装机验证成功!"
    echo ""
    echo "🚀 立即使用:"
    echo "sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 'proot-distro login ubuntu'"
else
    echo "❌ Ubuntu 装机验证失败"
    echo "请检查设备状态和网络连接"
fi