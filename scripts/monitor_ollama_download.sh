#!/bin/bash

# Ollama下载监控脚本
TARGET_HOST="172.24.4.71"
TARGET_PORT="8022"
TARGET_USER="u0_a306"
PASSWORD="123"

echo "📊 Ollama下载监控 - 按Ctrl+C退出"
echo "================================"

while true; do
    echo "$(date '+%H:%M:%S') - 检查下载状态..."
    
    # 检查下载进程
    processes=$(sshpass -p "$PASSWORD" ssh -p $TARGET_PORT $TARGET_USER@$TARGET_HOST "ps aux | grep 'ollama pull' | grep -v grep" 2>/dev/null)
    
    if [ -z "$processes" ]; then
        echo "✅ 所有下载已完成"
        break
    fi
    
    # 检查模型列表
    models=$(sshpass -p "$PASSWORD" ssh -p $TARGET_PORT $TARGET_USER@$TARGET_HOST "ollama list" 2>/dev/null)
    echo "当前模型:"
    echo "$models"
    
    # 检查磁盘使用
    disk_usage=$(sshpass -p "$PASSWORD" ssh -p $TARGET_PORT $TARGET_USER@$TARGET_HOST "du -sh ~/.ollama/models/blobs/" 2>/dev/null)
    echo "磁盘使用: $disk_usage"
    
    echo "---"
    sleep 10
done

echo "🎉 下载完成！最终模型列表:"
sshpass -p "$PASSWORD" ssh -p $TARGET_PORT $TARGET_USER@$TARGET_HOST "ollama list"