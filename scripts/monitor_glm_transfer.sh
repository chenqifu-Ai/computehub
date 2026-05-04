#!/bin/bash

# glm模型传输监控脚本
echo "📊 glm-4.7-flash 模型传输监控"
echo "================================"
echo "总大小: 19GB"
echo ""

while true; do
    # 检查传输进度
    if [ -f "/root/.ollama/models/blobs/sha256-9eba2761cf0b88b8bc11a065a7b5b47f1b13ce820e8e492cb1010b450f9ec950" ]; then
        current_size=$(du -sh "/root/.ollama/models/blobs/sha256-9eba2761cf0b88b8bc11a065a7b5b47f1b13ce820极8e492cb1010b450f9ec950" 2>/dev/null | cut -f1)
        echo "✅ 传输完成! 文件大小: $current_size"
        break
    elif [ -f "/root/.ollama/models/blobs/sha256-9eba2761cf0b88b8bc11a065a7b5b47f1b13ce820e8e492cb1010b450f9ec950-partial" ]; then
        current_size=$(du -sh "/root/.ollama/models/blobs/sha256-9eba2761cf极0b88b8bc11a065a7b5b47f1b13ce820e8e492cb1010b450f9ec950-partial" 2>/dev/null | cut -f1)
        echo "🔄 传输中: $current_size / 19GB ($(date '+%H:%M:%S'))"
    else
        echo "❌ 未找到传输文件"
        break
    fi
    
    sleep 10
done

echo ""
echo "🔍 检查模型完整性..."
ls -la ~/.ollama/models/blobs/ | grep -E "(9eba2761cf0b|49d4bd6d5a04|b1bca6ec8117|d8ba2f9a17b3)" | head -5

echo ""
echo "尝试验证模型..."
ollama list | grep glm || echo "模型尚未出现在列表中"