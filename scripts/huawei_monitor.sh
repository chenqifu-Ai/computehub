#!/bin/bash
# 华为手机构建监控脚本

TARGET_IP="192.168.1.9"
LOG_FILE="/root/.openclaw/workspace/monitor/huawei_build.log"

mkdir -p $(dirname "$LOG_FILE")

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # 检查网络连通性
    if ping -c 1 $TARGET_IP &>/dev/null; then
        # 检查构建进程
        SSH_STATUS=$(timeout 10 sshpass -p 123 ssh -p 8022 u0_a46@$TARGET_IP \
            "ps aux | grep -E '(npm|pnpm|node|tsc)' | head -3" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            echo "[$TIMESTAMP] ✅ 在线 - 构建进程: $(echo "$SSH_STATUS" | wc -l)" >> "$LOG_FILE"
            echo "$SSH_STATUS" >> "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ⚠️ 在线但SSH不可达" >> "$LOG_FILE"
        fi
    else
        echo "[$TIMESTAMP] ❌ 离线" >> "$LOG_FILE"
    fi
    
    sleep 300  # 5分钟检查一次
done