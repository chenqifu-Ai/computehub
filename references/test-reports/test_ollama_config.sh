#!/bin/bash
# 测试Ollama配置脚本

set -e

TARGET_HOST="192.168.2.156"
TARGET_PORT="8022"
TARGET_USER="u0_a46"
TARGET_PASS="123"

# 测试Ollama API连接
echo "测试Ollama API连接..."
if sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
    "curl -s -H 'Authorization: Bearer 8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii' https://api.ollama.com/v1/models | head -3"; then
    echo "✅ Ollama API连接成功"
else
    echo "❌ Ollama API连接失败"
fi

# 检查OpenClaw配置
echo "检查OpenClaw配置..."
sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
    "grep -A5 -B5 'ollama-cloud' ~/.openclaw/openclaw.json"

echo "配置完成！"