#!/bin/bash
# Ollama 自动切换脚本
# 检测本地服务器状态，自动切换本地/云端

CONFIG_FILE="$HOME/.openclaw/openclaw.json"
LOCAL_URL="http://192.168.1.7:11434/api/tags"
CLOUD_URL="https://ollama.com/api/tags"
CLOUD_KEY="8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

# 检测本地服务器
check_local() {
    curl -s --connect-timeout 3 "$LOCAL_URL" > /dev/null 2>&1
    return $?
}

# 检测云端服务器
check_cloud() {
    curl -s --connect-timeout 5 -H "Authorization: Bearer $CLOUD_KEY" "$CLOUD_URL" > /dev/null 2>&1
    return $?
}

# 切换到本地
switch_to_local() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 切换到本地服务器"
    sed -i 's/"primary": "ollama-cloud\/glm-5"/"primary": "ollama\/glm-5:cloud"/' "$CONFIG_FILE"
    pkill -f "openclaw-gateway" 2>/dev/null
    sleep 2
    nohup openclaw gateway > /tmp/gateway.log 2>&1 &
}

# 切换到云端
switch_to_cloud() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 切换到云端服务器"
    sed -i 's/"primary": "ollama\/glm-5:cloud"/"primary": "ollama-cloud\/glm-5"/' "$CONFIG_FILE"
    pkill -f "openclaw-gateway" 2>/dev/null
    sleep 2
    nohup openclaw gateway > /tmp/gateway.log 2>&1 &
}

# 主循环
main() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ollama自动切换脚本启动"
    
    while true; do
        if check_local; then
            # 本地可用，检查当前配置
            if grep -q '"primary": "ollama-cloud/glm-5"' "$CONFIG_FILE" 2>/dev/null; then
                switch_to_local
            fi
        else
            # 本地不可用，切换到云端
            if check_cloud; then
                if grep -q '"primary": "ollama/glm-5:cloud"' "$CONFIG_FILE" 2>/dev/null; then
                    switch_to_cloud
                fi
            fi
        fi
        
        sleep 30  # 每30秒检测一次
    done
}

main