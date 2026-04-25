#!/bin/bash
# Ollama Token 监控脚本
# 输出两种日志：简要摘要 + 详细记录
# 用法: bash scripts/ollama-token-monitor.sh [summary|detailed]

OLLAMA_HOST="http://127.0.0.1:11434"
LOG_DIR="/root/.openclaw/workspace/logs/ollama-token"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SUMMARY_FILE="$LOG_DIR/summary.txt"
DETAILED_FILE="$LOG_DIR/detailed.txt"

# 获取当前配置信息
echo "=== Ollama Token 监控 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查 Ollama 是否运行
if ! curl -s "$OLLAMA_HOST/api/tags" &>/dev/null; then
    echo "⚠️ Ollama 未运行，无法获取 token 信息"
    exit 1
fi

# 获取当前模型信息
MODEL_INFO=$(curl -s "$OLLAMA_HOST/api/tags" 2>/dev/null)

# 获取最新模型的 token 统计
# Ollama 的 /api/tags 不直接返回 token 使用统计
# 我们需要通过 /api/embeddings 或直接通过 /api/chat 来监控

# 显示当前加载的模型
echo "当前加载的模型："
echo "$MODEL_INFO" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    name = m.get('name', 'unknown')
    size = m.get('size', 0)
    digest = m.get('digest', '')[:12]
    print(f'  📦 {name}')
    print(f'     大小: {size / (1024*1024*1024):.1f} GB')
    print(f'     ID:   {digest}...')
    print()
" 2>/dev/null

# 检查 ollama 历史统计（如果有 ollama metrics 端点）
METRICS=$(curl -s "$OLLAMA_HOST/api/metrics" 2>/dev/null)
if [ -n "$METRICS" ]; then
    echo "=== 系统指标 ==="
    echo "$METRICS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'num_load' in data:
    print(f'  当前加载模型数: {data.get(\"num_load\", 0)}')
    print(f'  总加载次数: {data.get(\"num_load\", 0)}')
    print(f'  总请求数: {data.get(\"num_prompt\", 0) + data.get(\"num_predict\", 0)}')
" 2>/dev/null
fi

# 写入简要日志（摘要）
{
    echo "========================================="
    echo "Ollama Token 监控 - 简要摘要"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================="
    echo ""
    echo "当前模型:"
    echo "$MODEL_INFO" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    print(f'  📦 {m.get(\"name\", \"unknown\")} - {m.get(\"size\", 0) / (1024**3):.1f}GB')
" 2>/dev/null
    
    echo ""
    echo "状态: ✅ Ollama 运行中"
    echo "接口: $OLLAMA_HOST"
    echo "日志文件: $DETAILED_FILE"
    echo ""
    echo "-----------------------------------------"
    echo ""
} >> "$SUMMARY_FILE"

# 写入详细日志
{
    echo "========================================="
    echo "Ollama Token 监控 - 详细记录"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Host: $OLLAMA_HOST"
    echo "========================================="
    echo ""
    
    echo "--- 当前模型列表 ---"
    echo "$MODEL_INFO"
    echo ""
    
    echo "--- 系统信息 ---"
    echo "负载: $(uptime)"
    echo "内存: $(free -h | grep Mem)"
    echo "磁盘: $(df -h / | tail -1)"
    echo ""
    
    echo "-----------------------------------------"
    echo ""
} >> "$DETAILED_FILE"

echo "✅ 简要日志已保存: $SUMMARY_FILE"
echo "✅ 详细日志已保存: $DETAILED_FILE"
echo ""
echo "查看简要: cat $SUMMARY_FILE"
echo "查看详细: tail -50 $DETAILED_FILE"
