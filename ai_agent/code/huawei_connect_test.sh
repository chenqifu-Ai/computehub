#!/bin/bash

# 华为手机连接测试脚本
IP="10.35.204.26"
PORT="8022"
USER="u0_a46"
PASSWORD="123"

echo "尝试连接到华为手机 $USER@$IP:$PORT"

# 使用sshpass进行连接测试
if command -v sshpass >/dev/null 2>&1; then
    timeout 10 sshpass -p "$PASSWORD" ssh -p $PORT $USER@$IP "pwd && ls -la | head -5" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ SSH连接成功"
        exit 0
    else
        echo "❌ SSH连接失败"
        exit 1
    fi
else
    echo "⚠️ sshpass未安装，尝试普通连接"
    timeout 5 ssh -p $PORT $USER@$IP "echo '连接测试'" < /dev/null 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ SSH连接成功（无需密码）"
        exit 0
    else
        echo "❌ SSH连接失败，可能需要密码或密钥"
        exit 1
    fi
fi