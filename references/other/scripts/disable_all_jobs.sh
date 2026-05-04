#!/bin/bash
# 批量禁用所有启用的cron任务

echo "🛑 开始停止所有cron任务..."

# 获取所有启用的任务ID
ENABLED_JOBS=$(openclaw cron list | grep -E '"enabled": true' -B 10 | grep '"id":' | awk -F'"' '{print $4}')

if [ -z "$ENABLED_JOBS" ]; then
    echo "✅ 没有启用的cron任务需要停止"
    exit 0
fi

echo "📋 找到 $(echo "$ENABLED_JOBS" | wc -l) 个启用的任务"

# 禁用每个任务
COUNT=0
for JOB_ID in $ENABLED_JOBS; do
    echo "🔄 正在禁用任务: $JOB_ID"
    openclaw cron update "$JOB_ID" --enabled false
    if [ $? -eq 0 ]; then
        echo "✅ 已禁用: $JOB_ID"
        COUNT=$((COUNT+1))
    else
        echo "❌ 禁用失败: $JOB_ID"
    fi
    sleep 0.5

done

echo ""
echo "🎯 任务停止完成!"
echo "✅ 成功禁用: $COUNT 个任务"
echo "📊 总共: $(echo "$ENABLED_JOBS" | wc -l) 个任务"