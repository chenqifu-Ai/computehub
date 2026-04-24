#!/bin/bash

# 华为手机问题诊断脚本

echo "🔍 诊断华为手机OpenClaw问题..."

# 基本连接测试
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "echo '✅ SSH连接正常'"

# 检查OpenClaw可执行性
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "/data/data/com.termux/files/usr/bin/openclaw version && echo '✅ OpenClaw可执行' || echo '❌ OpenClaw执行失败'"

# 检查Node.js
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "node -v && echo '✅ Node.js正常' || echo '❌ Node.js问题'"

# 检查存储空间
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "df -h /data | tail -1 && echo '✅ 存储空间检查'"

# 检查内存
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "free -m | head -2 && echo '✅ 内存检查'"

echo ""
echo "📋 诊断完成"