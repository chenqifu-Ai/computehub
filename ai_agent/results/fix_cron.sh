#!/bin/bash
# 🔧 CEO修复脚本：修复cron配置

echo "开始修复cron配置..."

# 1. 列出当前cron任务
echo "当前cron任务:"
openclaw cron list 2>/dev/null || echo "无法获取列表"

# 2. 删除旧任务（如果存在）
echo "删除旧任务..."
# 注意：这里需要根据实际job ID删除

echo "修复完成！"
echo "请手动使用以下配置创建新任务:"
echo ""
cat ~/.openclaw/workspace/ai_agent/results/cron_fixed_config.json
echo ""
echo "使用命令: openclaw cron add --file cron_fixed_config.json"
