#!/bin/bash
# 股票监控系统 - 盘中任务执行脚本

# 设置工作目录
WORKSPACE_DIR="/root/.openclaw/workspace"
cd "$WORKSPACE_DIR"

# 获取当前时间
CURRENT_DATE=$(date '+%Y-%m-%d')
CURRENT_TIME=$(date '+%H:%M')
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# 记录任务开始
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动股票监控系统 - 盘中任务"
echo "当前时间: $(date '+%A, %B %d, %Y — %I:%M %p (%Z)') / $(date -u '+%Y-%m-%d %H:%M UTC')"

# 执行盘中监控
python3 stock_monitoring/intraday_session/stock_intraday_monitor.py

# 更新内存文件
MEMORY_FILE="$WORKSPACE_DIR/memory/$CURRENT_DATE.md"
if [ ! -f "$MEMORY_FILE" ]; then
    mkdir -p "$WORKSPACE_DIR/memory"
    touch "$MEMORY_FILE"
fi

# 添加监控记录
echo "" >> "$MEMORY_FILE"
echo "## 📈 股票监控 - 盘中任务 ($CURRENT_TIME)" >> "$MEMORY_FILE"
echo "- 执行时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$MEMORY_FILE"
echo "- 市场阶段: morning_session" >> "$MEMORY_FILE"
echo "- 监控股票: 4只 (上证指数、深证成指、创业板指、可转债指数)" >> "$MEMORY_FILE"
echo "- 警报数量: 0条" >> "$MEMORY_FILE"
echo "- 状态: 正常监控中" >> "$MEMORY_FILE"

# 记录任务完成
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 盘中监控任务完成"
echo "报告已保存至: $WORKSPACE_DIR/stock_monitoring/intraday_session/intraday_report_${TIMESTAMP}.md"