#!/bin/bash
# OpenClaw 新设备装机脚本
# 目标: 10.35.204.5, 用户: u0_a306, 版本: 2026.3.13

echo "🔧 OpenClaw 新设备装机"
echo "================================"
echo "目标设备: 10.35.204.5"
echo "用户名: u0_a306"
echo "版本: v2026.3.13"
echo "================================"

# 设备连接检查
check_connection() {
    echo "🔍 检查设备连接..."
    if ! ping -c 2 10.35.204.5 >/dev/null 2>&1; then
        echo "❌ 设备离线"
        return 1
    fi
    
    # 检查 SSH 连接
    if ! sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a306@10.35.204.5 "echo ✅ SSH连接测试" 2>/dev/null; then
        echo "❌ SSH 连接失败"
        return 1
    fi
    
    echo "✅ 设备连接正常"
    return 0
}

# 安装 OpenClaw
install_openclaw() {
    echo "📦 安装 OpenClaw v2026.3.13..."
    
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a306极10.35.204.5 << 'EOF'
    
    echo "🚀 开始安装 OpenClaw..."
    echo "================================"
    
    # 1. 检查 Node.js
    echo "1. 🔍 检查 Node.js 环境..."
    if command -v node >/dev/null 2>&1; then
        echo "✅ Node.js 已安装: $(node --version)"
        echo "✅ npm 已安装: $(npm --version)"
    else
        echo "❌ Node.js 未安装，需要先安装 Node.js"
        exit 1
    fi
    
    echo ""
    echo "2. 📦 安装 OpenClaw v2026.3.13..."
    
    # 尝试全局安装
    if npm install -g openclaw@2026.3.13 --force 2>&1; then
        echo "✅ 全局安装成功"
    else
        echo "⚠️  全局安装失败，尝试本地安装..."
        # 本地安装
        npm install openclaw@2026.3.13 --no-save 2>&1
        
        # 创建符号链接
        ln -s ~/node_modules/.bin/openclaw ~/openclaw
        chmod +x ~/openclaw
        echo "✅ 本地安装完成"
    fi
    
    echo ""
    echo "3. ✅ 安装验证..."
    if command -v openclaw >/dev/null 2>&1; then
        openclaw --version
        echo "✅ OpenClaw 安装成功!"
    else
        echo "❌ OpenClaw 安装失败"
        exit 1
    fi
    
    echo ""
    echo "4. 📁 创建配置目录..."
    mkdir -p ~/.openclaw
    echo "✅ 配置目录创建完成"
    
    echo "================================"
    echo "🎉 OpenClaw 安装完成!"
    echo "版本: v2026.3.13"
    echo "配置目录: ~/.openclaw"
    
