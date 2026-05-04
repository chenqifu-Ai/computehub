#!/bin/bash
# 安装状态检查脚本
echo "🔍 OpenClaw 安装状态检查"
echo "================================"

# 检查设备连接
ping -c 1 10.35.204.5 >/dev/null 2>&1 || {
    echo "❌ 设备 10.35.204.5 离线"
    exit 1
}

echo "✅ 设备在线"

# 检查安装状态
sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a306@10.35.204.5 "
# 安装状态检查
echo "📊 安装状态详情"
echo "================================"

echo "1. 🔧 基础环境:"
echo "用户: $(whoami)"
echo "Node.js: $(node --version 2>/dev/null || echo '未安装')"
echo "npm: $(npm --version 2>/dev/null || echo '未安装')"
echo "git: $(git --version 2>/dev/null | head -1 || echo '未安装')"

echo ""
echo "2. 📦 OpenClaw 状态:"
if [ -f ~/openclaw ] && [ -x ~/openclaw ]; then
    echo "✅ OpenClaw 已安装且可执行"
    echo "版本: $(~/openclaw --version 2>/dev/null | head -1 || echo '未知')"
    echo "路径: ~/openclaw"
elif [ -f ~/node_modules/.bin/openclaw ]; then
    echo "⚠️  OpenClaw 文件存在，需要链接"
    echo "位置: ~/node_modules/.bin/openclaw"
    echo "大小: $(du -h ~/node_modules/.bin/openclaw 2>/dev/null | cut -f1 || echo '未知')"
else
    echo "❌ OpenClaw 未安装"
    echo "建议: npm install openclaw@2026.3.13 --no-save"
fi

echo ""
echo "3. 📁 配置目录:"
if [ -d ~/.openclaw ]; then
    echo "✅ 配置目录存在"
    echo "大小: $(du -sh ~/.openclaw 2>/dev/null | cut -f1 || echo '空')"
else
    echo "❌ 配置目录不存在"
    echo "建议: mkdir -p ~/.openclaw"
fi

echo ""
echo "4. 🌐 网络状态:"
echo "IP: 10.35.204.5"
echo "连接: ✅ SSH 正常"
echo "环境: Termux + Node.js"

echo "================================"
"