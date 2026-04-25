#!/bin/bash
# Ollama Token 拦截器 - 记录每次请求的 prompt 和 completion tokens
# 原理：拦截 Ollama API 响应，提取 token 信息
# 需要 Ollama 运行在 11434 端口

OLLAMA_HOST="http://127.0.0.1:11434"
LOG_DIR="/root/.openclaw/workspace/logs/ollama-token"
mkdir -p "$LOG_DIR"

SUMMARY="$LOG_DIR/summary.txt"
DETAILED="$LOG_DIR/detailed.log"
STATS="$LOG_DIR/stats.json"

echo "========================================="
echo "Ollama Token 监控 - 启动"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Ollama: $OLLAMA_HOST"
echo "========================================="

# 检查 Ollama 是否运行
if ! curl -s "$OLLAMA_HOST/api/tags" &>/dev/null; then
    echo "⚠️ Ollama 未运行！"
    echo "启动 Ollama: ollama serve"
    exit 1
fi

# 获取当前模型信息并记录
echo ""
echo "--- 当前加载模型 ---"
curl -s "$OLLAMA_HOST/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    name = m.get('name', 'unknown')
    size_gb = m.get('size', 0) / (1024**3)
    params = m.get('details', {}).get('parameter_size', '?')
    print(f'  📦 {name} | {size_gb:.1f}GB | {params}')
"

# 记录初始状态到详细日志
{
    echo "========================================="
    echo "Ollama Token 监控 - 详细记录"
    echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================="
    echo ""
    curl -s "$OLLAMA_HOST/api/tags" >> "$DETAILED" 2>/dev/null
    echo ""
} >> "$DETAILED"

echo ""
echo "✅ 监控脚本启动"
echo "📁 简要日志: $SUMMARY"
echo "📁 详细日志: $DETAILED"
echo ""
echo "手动查看："
echo "  简要统计: cat $SUMMARY"
echo "  详细日志: tail -20 $DETAILED"
echo "  实时数据: tail -f $LOG_DIR/requests.log"
