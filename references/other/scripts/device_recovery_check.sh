#!/bin/bash
# 设备恢复检查脚本
# 持续监控设备 10.35.204.243 状态并在恢复后执行 Node.js 重装

echo "🔍 设备恢复监控脚本"
echo "================================"
echo "目标设备: 10.35.204.243"
echo "监控间隔: 30秒"
echo "最大等待: 10分钟"
echo "================================"

MAX_WAIT=600  # 10分钟
CHECK_INTERVAL=30
start_time=$(date +%s)

echo "⏰ 开始监控设备状态..."

while true; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    
    # 检查是否超时
    if [ $elapsed_time -ge $MAX_WAIT ]; then
        echo "❌ 监控超时 (10分钟)，设备仍未恢复"
        echo "请手动检查设备状态"
        exit 1
    fi
    
    echo "🔄 检查设备状态 ($((elapsed_time))秒)..."
    
    # 检查设备在线状态
    if ping -c 2 10.35.204.243 >/dev/null 2>&1; then
        echo "✅ 设备恢复在线!"
        
        # 检查 SSH 服务
        if timeout 5 nc -zv 10.35.204.243 8022 2>/dev/null; then
            echo "✅ SSH 服务正常"
            echo ""
            echo "🚀 执行 Node.js 重装..."
            
            # 执行重装脚本
            if [ -f "./reinstall_nodejs.sh" ]; then
                chmod +x ./reinstall_nodejs.sh
                ./reinstall_nodejs.sh
                exit $?
            else
                echo "❌ 重装脚本未找到"
                exit 1
            fi
        else
            echo "⚠️  设备在线但 SSH 服务未启动"
            echo "请在设备上执行: sshd"
            sleep $CHECK_INTERVAL
            continue
        fi
    else
        echo "❌ 设备仍然离线，等待 $CHECK_INTERVAL 秒后重试..."
        sleep $CHECK_INTERVAL
    fi
done