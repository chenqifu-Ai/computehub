#!/bin/bash
# OpenClaw 最终安装脚本 - 包含所有安装方法
# 目标: 10.35.204.243, 用户: u0_a165, 密码: 123

echo "🎯 OpenClaw 最终安装脚本"
echo "================================"

# 检查设备状态
echo "🔍 检查设备连接..."
if ! ping -c 2 10.35.204.243 >/dev/null 2>&1; then
    echo "❌ 设备离线"
    exit 1
fi

echo "✅ 设备在线"

# 安装函数 - 尝试所有方法
install_openclaw_all_methods() {
    echo "🚀 尝试所有安装方法..."
    
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a165@10.35.204.243 << 'EOF'
    
    echo "📦 方法 1: npm 标准安装"
    npm install -g openclaw@2026.3.13 --force 2>&1 | tail -3
    
    if command -v openclaw >/dev/null 2>&1; then
        echo "✅ 方法1成功"
        exit 0
    fi
    
    echo ""
    echo "📦 方法 2: 使用特定 registry"
    npm install -g openclaw@2026.3.13 --registry=https://registry.npmjs.org/ --no-audit 2>&1 | tail -3
    
    if command -v openclaw >/dev/null 2>&1; then
        echo "✅ 方法2成功"
        exit 0
    fi
    
    echo ""
    echo "📦 方法 3: 使用 yarn"
    if ! command -v yarn >/dev/null 2>&1; then
        npm install -g yarn
    fi
    yarn global add openclaw@2026.3.13 2>&1 | tail -3
    
    if command -v openclaw >/dev/null 2>&1; then
        echo "✅ 方法3成功"
        exit 0
    fi
    
    echo ""
    echo "📦 方法 4: 源码安装"
    cd /tmp
    rm -rf openclaw 2>/dev/null
    git clone https://github.com/openclaw/openclaw.git 2>/dev/null
    cd openclaw
    git checkout v2026.3.13 2>/dev/null
    npm install 2>&1 | tail -3
    
    if [ -f bin/openclaw.js ]; then
        ln -sf /tmp/openclaw/bin/openclaw.js ~/openclaw
        chmod +x ~/openclaw
        echo "✅ 方法4成功"
        exit 0
    fi
    
    echo ""
    echo "❌ 所有方法都失败"
    echo "请检查错误日志: ~/.npm/_logs/"
    exit 1
EOF
}

# 执行安装
install_openclaw_all_methods

echo ""
echo "🎯 安装结果验证:"
echo "================================"

if sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 "command -v openclaw >/dev/null 2>&1 || [ -f ~/openclaw ]"; then
    echo "✅ OpenClaw 安装成功!"
    sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.243 "
        if command -v openclaw >/dev/null 2>&1; then
            openclaw --version
        else
            ~/openclaw --version
        fi
    "
else
    echo "❌ OpenClaw 安装失败"
    echo "所有安装方法都尝试过了"
fi

echo "================================"