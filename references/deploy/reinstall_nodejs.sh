#!/bin/bash
# Node.js 重装脚本 - 解决镜像源问题
# 目标: 10.35.204.243, 用户: u0_a165, 密码: 123

echo "🎯 Node.js 重装脚本"
echo "================================"

# 检查设备状态
echo "🔍 检查设备连接..."
if ! ping -c 2 10.35.204.243 >/dev/null 2>&1; then
    echo "❌ 设备 10.35.204.243 离线"
    echo "请确保设备开机并连接网络"
    exit 1
fi

echo "✅ 设备在线"

# 清理 SSH 主机密钥
echo "🔧 清理 SSH 主机密钥..."
ssh-keygen -R "[10.35.204.243]:8022" 2>/dev/null
ssh-keyscan -p 8022 10.35.204.243 2>/dev/null >> ~/.ssh/known_hosts

echo "✅ SSH 配置完成"

# Node.js 重装函数
reinstall_nodejs() {
    echo "🚀 开始重装 Node.js..."
    
    # 通过 SSH 执行重装
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a165@10.35.204.243 << 'EOF'
    
    echo "📦 步骤 1: 修复包管理器镜像源"
    echo "尝试更新包列表..."
    pkg update --fix-missing
    
    echo ""
    echo "📦 步骤 2: 清理旧 Node.js 安装"
    pkg uninstall nodejs -y 2>/dev/null
    rm -rf /data/data/com.termux/files/usr/lib/node_modules 2>/dev/null
    
    echo ""
    echo "📦 步骤 3: 使用不同镜像源安装"
    echo "尝试主镜像..."
    pkg install nodejs -y 2>&1 | tail -5
    
    # 如果主镜像失败，尝试备用方法
    if ! command -v node >/dev/null 2>&1; then
        echo ""
        echo "🔄 主镜像失败，尝试备用方法..."
        echo "1. 使用 curl 直接下载..."
        
        # 尝试直接下载安装包
        cd ~
        curl -O https://termux.net/dists/stable/main/binary-aarch64/nodejs_25.8.2_aarch64.deb 2>/dev/null \
            && dpkg -i nodejs_25.8.2_aarch64.deb 2>/dev/null \
            && echo "✅ 直接下载安装成功" \
            || echo "❌ 直接下载失败"
    fi
    
    echo ""
    echo "✅ 步骤 4: 验证安装"
    if command -v node >/dev/null 2>&1; then
        echo "🎉 Node.js 安装成功!"
        echo "版本: $(node -v)"
        echo "npm 版本: $(npm -v)"
    else
        echo "❌ Node.js 安装失败"
        echo "错误信息:"
        pkg install nodejs -y 2>&1 | tail -3
    fi
    
    echo ""
    echo "🔧 步骤 5: 环境验证"
    echo "Node.js 路径: $(which node 2>/dev/null || echo '未找到')"
    echo "npm 路径: $(which npm 2>/dev/null || echo '未找到')"
EOF
}

# 执行重装
reinstall_nodejs

echo ""
echo "🎯 重装结果总结:"
echo "📍 目标设备: 10.35.204.243"
echo "👤 用户名: u0_a165"
echo "🔑 密码: 123"
echo "🟢 组件: Node.js + npm"
echo "================================"

# 最终验证
echo "🔍 最终验证..."
if sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 "command -v node >/dev/null 2>&1"; then
    echo "✅ Node.js 重装验证成功!"
    sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 "node -v; npm -v"
else
    echo "❌ Node.js 重装验证失败"
    echo "需要手动检查设备状态"
fi