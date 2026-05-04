#!/bin/bash
# 完整的 OpenClaw 装机脚本
# 目标: 10.35.204.243, 用户: u0_a165, 密码: 123, 版本: v2026.3.13

echo "🎯 OpenClaw 装机脚本 - 完整版"
echo "================================"

# 清理 SSH 主机密钥
echo "🔧 清理 SSH 主机密钥..."
ssh-keygen -R "[10.35.204.243]:8022" 2>/dev/null
ssh-keyscan -p 8022 10.35.204.243 2>/dev/null >> ~/.ssh/known_hosts

echo "✅ SSH 配置完成"

# 安装函数
install_openclaw() {
    echo "🚀 开始安装 OpenClaw v2026.3.13..."
    
    # 通过 SSH 执行完整安装
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a165@10.35.204.243 << 'EOF'
    
    echo "📦 步骤 1: 更新包管理器"
    pkg update -y
    
    echo "📦 步骤 2: 安装 Node.js"
    pkg install nodejs -y
    
    echo "🔍 步骤 3: 验证 Node.js 环境"
    node -v && echo "✅ Node.js 安装成功" || echo "❌ Node.js 安装失败"
    npm -v && echo "✅ npm 安装成功" || echo "❌ npm 安装失败"
    
    echo "🚀 步骤 4: 安装 OpenClaw v2026.3.13"
    npm install -g openclaw@2026.3.13 --force
    
    echo "✅ 步骤 5: 验证安装"
    if command -v openclaw >/dev/null 2>&1; then
        echo "🎉 OpenClaw 安装成功!"
        openclaw --version
        echo ""
        echo "🦞 OpenClaw 使用指南:"
        echo "启动: openclaw --help"
        echo "TUI: openclaw tui"
        echo "Gateway: openclaw gateway start"
    else
        echo "❌ 全局安装失败，尝试本地安装..."
        cd ~
        npm install openclaw@2026.3.13 --no-save
        
        if [ -f ~/node_modules/.bin/openclaw ]; then
            ln -sf ~/node_modules/.bin/openclaw ~/openclaw
            chmod +x ~/openclaw
            echo "✅ 本地安装 + 手动链接成功"
            ~/openclaw --version
        else
            echo "❌ 所有安装方式都失败"
        fi
    fi
EOF
}

# 执行安装
install_openclaw

echo ""
echo "🎯 装机结果总结:"
echo "📍 目标设备: 10.35.204.243"
echo "👤 用户名: u0_a165"
echo "🔑 密码: 123"
echo "🦞 版本: OpenClaw v2026.3.13"
echo "🔧 环境: Node.js + npm"
echo "================================"

# 最终验证
echo "🔍 最终验证..."
if sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 "command -v openclaw >/dev/null 2>&1 || [ -f ~/openclaw ]"; then
    echo "✅ OpenClaw 装机验证成功!"
    echo ""
    echo "🚀 立即使用:"
    echo "sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 'openclaw --version'"
else
    echo "❌ OpenClaw 装机验证失败"
    echo "请检查设备状态和网络连接"
fi