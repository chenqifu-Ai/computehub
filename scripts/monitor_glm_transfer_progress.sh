#!/bin/bash

echo "📊 glm-4.7-flash 模型传输进度监控"
echo "===================================="
echo "目标大小: 19.0 GB"
echo ""

while true; do
    if pgrep -f "sshpass.*scp" > /dev/null; then
        current_size=$(du -sh ~/.ollama/models/blobs/sha256-9eba2761cf0b88b8bc11a065a7b5b47f1b13ce820e8e492cb1010b450f9ec950 2>/dev/null | cut -f1)
        if [ -n "$current_size" ]; then
            echo "🔄 传输中: $current_size / 19.0 GB ($(date '+%H:%M:%S'))"
        else
            echo "⏳ 传输准备中... ($(date '+%H:%M:%S'))"
        fi
    else
        final_size=$(du -sh ~/.ollama/models/blobs/sha256-9eba2761cf0b88b8bc11a065a7b5b47f1b13ce820e8e492cb1010b450f9ec950 2>/dev/null | cut -f1)
        if [ -n "$final_size" ]; then
            echo "✅ 传输完成! 最终大小: $final_size"
        else
            echo "❌ 传输中断或未开始"
        fi
        break
    fi
    sleep 10
done