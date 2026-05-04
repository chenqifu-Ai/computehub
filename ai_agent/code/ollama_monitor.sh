#!/bin/bash
# Ollama 模型下载监控脚本

SERVER="192.168.2.165:11434"
MODEL="ministral-3:14b"

echo "========================================"
echo "📥 Ollama 模型下载监控"
echo "   服务器：$SERVER"
echo "   模型：$MODEL"
echo "========================================"
echo ""

# 启动后台下载
curl -s http://$SERVER/api/pull -d "{\"name\":\"$MODEL\"}" > /tmp/ollama_pull.log 2>&1 &
PULL_PID=$!

echo "✅ 下载已启动 (PID: $PULL_PID)"
echo ""

# 监控进度
LAST_SIZE=0
LAST_TIME=$(date +%s)

while kill -0 $PULL_PID 2>/dev/null; do
    # 读取最新进度
    LINE=$(tail -1 /tmp/ollama_pull.log 2>/dev/null)
    
    if echo "$LINE" | grep -q '"status":"success"'; then
        echo ""
        echo "========================================"
        echo "✅ 下载完成!"
        echo "========================================"
        break
    fi
    
    # 解析进度
    PROGRESS=$(echo "$LINE" | grep -oP '"progress":\s*\K[\d.]+' 2>/dev/null)
    COMPLETED=$(echo "$LINE" | grep -oP '"completed":\s*\K\d+' 2>/dev/null)
    TOTAL=$(echo "$LINE" | grep -oP '"total":\s*\K\d+' 2>/dev/null)
    
    if [ -n "$COMPLETED" ] && [ -n "$TOTAL" ]; then
        # 计算百分比
        if [ "$TOTAL" -gt 0 ]; then
            PERCENT=$(echo "scale=1; $COMPLETED * 100 / $TOTAL" | bc 2>/dev/null || echo "?")
        fi
        
        # 计算速度
        CURRENT_TIME=$(date +%s)
        TIME_DIFF=$((CURRENT_TIME - LAST_TIME))
        SIZE_DIFF=$((COMPLETED - LAST_SIZE))
        
        if [ "$TIME_DIFF" -gt 0 ]; then
            SPEED=$((SIZE_DIFF / TIME_DIFF / 1024 / 1024))
            REMAINING=$((TOTAL - COMPLETED))
            if [ "$SPEED" -gt 0 ]; then
                ETA=$((REMAINING / SPEED / 1024 / 1024))
                ETA_MIN=$((ETA / 60))
                ETA_SEC=$((ETA % 60))
            else
                ETA_MIN="?"
                ETA_SEC="?"
            fi
        else
            SPEED=0
            ETA_MIN="?"
            ETA_SEC="?"
        fi
        
        # 格式化大小
        COMPLETED_GB=$(echo "scale=2; $COMPLETED / 1073741824" | bc 2>/dev/null || echo "?")
        TOTAL_GB=$(echo "scale=2; $TOTAL / 1073741824" | bc 2>/dev/null || echo "?")
        
        # 打印进度条
        BAR_LEN=40
        FILLED=$(echo "$PERCENT * $BAR_LEN / 100" | bc 2>/dev/null || echo "0")
        EMPTY=$((BAR_LEN - FILLED))
        BAR=$(printf '%*s' "$FILLED" | tr ' ' '█')$(printf '%*s' "$EMPTY" | tr ' ' '░')
        
        printf "\r[%s] %5s%% | %s/%s GB | 速度：%d MB/s | 预计：%02d:%02d" \
            "$BAR" "$PERCENT" "$COMPLETED_GB" "$TOTAL_GB" "$SPEED" "$ETA_MIN" "$ETA_SEC"
        
        LAST_SIZE=$COMPLETED
        LAST_TIME=$CURRENT_TIME
    fi
    
    sleep 2
done

echo ""
echo ""
echo "📊 最终状态:"
curl -s http://$SERVER/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  ✅ {m[\"name\"]} - {m[\"size\"]/1e9:.2f}GB') for m in d.get('models',[])]" 2>/dev/null || echo "  无法获取模型列表"
