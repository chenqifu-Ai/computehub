#!/bin/bash
# 保护 openclaw-tui 进程不被杀死

LOG_FILE="/root/.openclaw/logs/protect.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "$(date): 启动 openclaw-tui 保护进程" >> "$LOG_FILE"

while true; do
    # 检查 openclaw-tui 进程数量
    TUI_COUNT=$(pgrep -f "openclaw-tui" | wc -l)
    
    if [ "$TUI_COUNT" -eq 0 ]; then
        echo "$(date): 检测到 openclaw-tui 进程被杀死，正在重启..." >> "$LOG_FILE"
        # 重启 openclaw-tui
        nohup openclaw tui --gateway-url http://192.168.1.17:18789 --token 2159c9affb69a78acdef02bc0e0c68824bedcc8ccf11bc5b > /dev/null 2>&1 &
        sleep 5
        NEW_COUNT=$(pgrep -f "openclaw-tui" | wc -l)
        echo "$(date): 重启完成，当前进程数: $NEW_COUNT" >> "$LOG_FILE"
    elif [ "$TUI_COUNT" -gt 2 ]; then
        echo "$(date): 检测到过多 openclaw-tui 进程 ($TUI_COUNT)，可能需要清理" >> "$LOG_FILE"
        # 这里不自动清理，只记录日志
    fi
    
    sleep 30
done