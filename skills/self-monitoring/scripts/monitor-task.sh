#!/bin/bash

# 🎯 任务自我监控脚本

# 默认参数
PROCESS_PATTERN=""
TIMEOUT=300      # 5分钟超时
CHECK_INTERVAL=5 # 检查间隔(秒)
MAX_CHECKS=60    # 最大检查次数
TARGET_HOST=""
TARGET_USER=""
TARGET_PASS=""
TARGET_PORT=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --process)
            PROCESS_PATTERN="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --check-interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        --max-checks)
            MAX_CHECKS="$2"
            shift 2
            ;;
        --host)
            TARGET_HOST="$2"
            shift 2
            ;;
        --user)
            TARGET_USER="$2"
            shift 2
            ;;
        --pass)
            TARGET_PASS="$2"
            shift 2
            ;;
        --port)
            TARGET_PORT="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 验证必要参数
if [ -z "$PROCESS_PATTERN" ]; then
    echo "错误: 必须指定 --process 参数"
    exit 1
fi

# 监控函数
monitor_process() {
    local check_count=0
    local start_time=$(date +%s)
    
    echo "🔄 开始监控进程: $PROCESS_PATTERN"
    echo "⏰ 超时时间: ${TIMEOUT}秒"
    echo "📊 检查间隔: ${CHECK_INTERVAL}秒"
    echo "---"
    
    while [ $check_count -lt $MAX_CHECKS ]; do
        check_count=$((check_count + 1))
        current_time=$(date +%s)
        elapsed_time=$((current_time - start_time))
        
        # 检查超时
        if [ $elapsed_time -ge $TIMEOUT ]; then
            echo "❌ 监控超时 (${elapsed_time}秒)"
            return 2
        fi
        
        # 执行监控检查
        echo "=== 监控检查 #${check_count} (经过 ${elapsed_time}秒) ==="
        
        if [ -n "$TARGET_HOST" ]; then
            # 远程监控
            sshpass -p "$TARGET_PASS" ssh -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
                "ps aux | grep -E '$PROCESS_PATTERN' | grep -v grep && \
                 top -n 1 -b | grep -E '$PROCESS_PATTERN' | head -1"
        else
            # 本地监控
            ps aux | grep -E "$PROCESS_PATTERN" | grep -v grep
            top -n 1 -b | grep -E "$PROCESS_PATTERN" | head -1
        fi
        
        # 检查进程是否存在
        if [ $? -eq 0 ]; then
            echo "✅ 进程正常运行中"
        else
            echo "❌ 进程不存在或已停止"
            return 1
        fi
        
        echo "---"
        sleep $CHECK_INTERVAL
    done
    
    echo "✅ 监控完成，进程持续运行 ${elapsed_time}秒"
    return 0
}

# 执行监控
monitor_process
exit_code=$?

# 根据退出码处理结果
case $exit_code in
    0)
        echo "🎉 监控成功完成"
        ;;
    1)
        echo "⚠️  进程异常停止，需要干预"
        ;;
    2)
        echo "⏰ 监控超时，可能需要检查任务状态"
        ;;
    *)
        echo "❓ 未知监控结果"
        ;;
esac

exit $exit_code