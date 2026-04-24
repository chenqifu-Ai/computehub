#!/bin/bash

# Ollama模型文件拷贝脚本
TARGET_HOST="172.24.4.71"
TARGET_USER="root"  # 根据实际情况修改用户名
TARGET_PATH="/root/.ollama/models"  # 目标路径

echo "📦 开始拷贝Ollama模型文件到 $TARGET_HOST"
echo "============================================"

# 检查源模型文件
echo "🔍 检查本地模型文件..."
LOCAL_MODELS_PATH="/root/.ollama/models"

if [ ! -d "$LOCAL_MODELS_PATH" ]; then
    echo "❌ 本地模型目录不存在: $LOCAL_MODELS_PATH"
    exit 1
fi

echo "✅ 本地模型目录存在"

# 显示模型文件大小
echo "📊 模型文件大小统计:"
du -sh $LOCAL_MODELS_PATH

echo ""
echo "📁 详细文件结构:"
find $LOCAL_MODELS_PATH -type f -name "*.bin" -o -name "*.gguf" -o -name "*.json" | head -10

echo ""
# 检查网络连通性
echo "🔌 检查目标服务器连通性..."
if ping -c 2 $TARGET_HOST >/dev/null 2>&1; then
    echo "✅ 目标服务器可达"
else
    echo "❌ 无法连接到 $TARGET_HOST"
    echo "请确保目标服务器网络可达"
    exit 1
fi

# 检查目标目录
echo "🔍 检查目标服务器目录..."
if ssh $TARGET_USER@$TARGET_HOST "[ -d '$TARGET_PATH' ]" 2>/dev/null; then
    echo "✅ 目标目录已存在"
else
    echo "⚠️ 目标目录不存在，将创建"
    ssh $TARGET_USER@$TARGET_HOST "mkdir -p '$TARGET_PATH'"
fi

# 确认拷贝
echo ""
echo "⚠️  即将开始拷贝，请确认:"
echo "源目录: $LOCAL_MODELS_PATH"
echo "目标: $TARGET_USER@$TARGET_HOST:$TARGET_PATH"
echo "预计大小: $(du -sh $LOCAL_MODELS_PATH | cut -f1)"
echo ""
read -p "是否继续? (y/N): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "操作取消"
    exit 0
fi

# 开始拷贝
echo "🚀 开始拷贝模型文件..."

# 使用rsync进行增量拷贝（推荐）
if command -v rsync >/dev/null 2>&1; then
    echo "使用rsync进行智能拷贝..."
    rsync -avz --progress $LOCAL_MODELS_PATH/ $TARGET_USER@$TARGET_HOST:$TARGET_PATH/
else
    echo "使用scp进行拷贝..."
    scp -r $LOCAL_MODELS_PATH/* $TARGET_USER@$TARGET_HOST:$TARGET_PATH/
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 拷贝完成!"
    
    # 验证拷贝结果
    echo "🔍 验证拷贝结果..."
    ssh $TARGET_USER@$TARGET_HOST "du -sh '$TARGET_PATH'"
    
    echo ""
    echo "🎉 模型文件拷贝成功!"
    echo "在目标服务器上运行: ollama serve 启动服务"
else
    echo ""
    echo "❌ 拷贝失败"
    exit 1
fi