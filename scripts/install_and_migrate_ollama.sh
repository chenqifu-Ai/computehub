#!/bin/bash

# Ollama 安装和模型迁移脚本
TARGET_HOST="172.24.4.71"

echo "🤖 开始为 $TARGET_HOST 安装 Ollama 并迁移模型"
echo "================================================"

# 1. 检查网络连通性
echo "🔍 检查网络连通性..."
ping -c 3 $TARGET_HOST
if [ $? -ne 0 ]; then
    echo "❌ 无法连接到 $TARGET_HOST"
    exit 1
fi

echo "✅ 网络连通性正常"

# 2. 在远程服务器安装Ollama
echo "📦 在远程服务器安装Ollama..."
ssh $TARGET_HOST << 'EOF'
# 检查是否已安装Ollama
if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama 已安装"
    ollama --version
else
    echo "安装Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    # 启动Ollama服务
    echo "启动Ollama服务..."
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3
    
    echo "✅ Ollama 安装完成"
    ollama --version
fi
EOF

# 3. 迁移模型
echo "🚀 开始迁移模型到 $TARGET_HOST"

# 获取本地模型列表
MODELS=$(ollama list | awk 'NR>1 {print $1}')

echo "📊 需要迁移的模型:"
echo "$MODELS"
echo ""

# 逐个迁移模型
for model in $MODELS; do
    echo "🔄 迁移模型: $model"
    
    # 在远程服务器拉取模型
    ssh $TARGET_HOST "ollama pull $model"
    
    if [ $? -eq 0 ]; then
        echo "✅ $model 迁移成功"
    else
        echo "❌ $model 迁移失败"
    fi
    echo ""
done

# 4. 验证迁移结果
echo "🔍 验证迁移结果..."
echo "本地模型:"
ollama list

echo ""
echo "远程模型:"
ssh $TARGET_HOST "ollama list"

echo ""
echo "🎉 迁移完成！"
echo "远程服务器 $TARGET_HOST 现在可以使用所有模型"