#!/bin/bash
# 紧急修复Commander.js模块错误

echo "🚨 紧急修复 OpenClaw Commander.js 模块错误"
echo "📱 设备: 192.168.1.9 (华为手机)"
echo "⏰ 开始时间: $(date)"
echo "=========================================="

# 1. 备份当前安装
echo "📦 备份当前安装..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "cp -r /data/data/com.termux/files/usr/lib/node_modules/openclaw /tmp/openclaw-backup-$(date +%s)"

# 2. 清理旧安装
echo "🧹 清理旧安装..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "rm -rf /data/data/com.termux/files/usr/lib/node_modules/openclaw"

# 3. 重新安装
echo "🔧 重新安装OpenClaw..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "npm install -g openclaw@2026.3.13 --no-fund --no-audit --force"

# 4. 修复符号链接
echo "🔗 修复符号链接..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "rm -f /data/data/com.termux/files/usr/bin/openclaw && \
     ln -s ../lib/node_modules/openclaw/openclaw.mjs /data/data/com.termux/files/usr/bin/openclaw"

# 5. 验证修复
echo "✅ 验证修复..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "chmod +x /data/data/com.termux/files/usr/bin/openclaw && \
     openclaw --version 2>/dev/null && echo '🎉 修复成功!' || echo '❌ 需要手动检查'"

echo "=========================================="
echo "修复完成时间: $(date)"
echo "如果仍有问题，请尝试在Ubuntu环境中重新安装:"
echo "proot-distro login ubuntu -- npm install -g openclaw"