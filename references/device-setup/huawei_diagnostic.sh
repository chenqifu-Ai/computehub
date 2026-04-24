#!/bin/bash

# 华为手机深度诊断

echo "🔍 华为手机深度诊断..."

# 1. 检查基础环境
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "
echo '=== 系统信息 ==='
uname -a
echo ''

echo '=== Node.js版本 ==='
node -v
npm -v
echo ''

echo '=== 存储空间 ==='
df -h /data
echo ''

echo '=== 内存状态 ==='
free -m
echo ''

echo '=== OpenClaw安装 ==='
ls -la /data/data/com.termux/files/usr/bin/openclaw
echo ''

echo '=== 尝试直接运行 ==='
cd /data/data/com.termux/files/home
 timeout 5 /data/data/com.termux/files/usr/bin/openclaw version
echo '退出码: $?'
"

echo ""
echo "📋 诊断完成"