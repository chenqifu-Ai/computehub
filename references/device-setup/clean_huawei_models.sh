#!/bin/bash
# 清理华为手机上的OpenClaw模型配置

HUAWEI_IP="192.168.1.9"
HUAWEI_USER="u0_a46"
HUAWEI_PASSWORD="123"
SSH_PORT="8022"

echo "🧹 清理华为手机上的模型配置..."

# 备份原配置
sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT -o StrictHostKeyChecking=no $HUAWEI_USER@$HUAWEI_IP \
    "cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.clean"

echo "✅ 配置已备份"

# 简化模型配置 - 只保留几个核心模型
echo "📋 简化模型列表..."

sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT -o StrictHostKeyChecking=no $HUAWEI_USER@$HUAWEI_IP << 'EOF'
# 在华为手机上执行的命令
cd ~/.openclaw

# 使用sed简化模型配置
sed -i '/"models": {/,/^      }/{
    /"models": {/b
    /^      }/b
    /"modelstudio\/qwen3\.5-flash": {}/b
    /"modelstudio\/qwen3\.5-plus": {}/b  
    /"ollama-cloud\/deepseek-v3\.1:671b": {}/b
    /"ollama\/llama3:latest": {}/b
    d
}' openclaw.json

echo "模型配置已简化"
EOF

echo "✅ 模型配置已简化"
echo "🎯 保留的模型:"
echo "  - modelstudio/qwen3.5-flash (默认)"
echo "  - modelstudio/qwen3.5-plus"
echo "  - ollama-cloud/deepseek-v3.1:671b"
echo "  - ollama/llama3:latest"

echo "✅ 华为手机模型配置清理完成"