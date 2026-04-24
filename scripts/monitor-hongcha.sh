#!/bin/bash

# 监控红茶虚拟机的 OpenClaw 进程
# 如果被杀死，自动重启

TARGET_HOST="192.168.1.3"
TARGET_USER="chen"
TARGET_PASS="c9fc9f,."

while true; do
    # 检查 OpenClaw 进程是否存在
    if ! sshpass -p "$TARGET_PASS" ssh "$TARGET_USER@$TARGET_HOST" "pgrep -f openclaw-gateway" > /dev/null 2>&1; then
        echo "$(date): OpenClaw 在 $TARGET_HOST 上被杀死，正在重启..."
        
        # 重启 OpenClaw
        sshpass -p "$TARGET_PASS" ssh "$TARGET_USER@$TARGET_HOST" "pkill -f openclaw && sleep 3 && nohup openclaw gateway start > /dev/null 2>&1 &"
        
        echo "$(date): OpenClaw 重启完成"
    fi
    
    # 每30秒检查一次
    sleep 30
done