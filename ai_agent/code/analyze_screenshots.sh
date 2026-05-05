#!/bin/bash
# 批量截图识别 - 通过 API 分析
API_URL="http://127.0.0.1:8765/v1/chat/completions"
API_KEY="sk-78sadn09bjawde123e"
IMAGES_DIR="/root/.openclaw/workspace/_temp_image_recognition/20260501-new"
PROMPT="请用中文分析这张截图，说明：1)这是什么内容 2)关键信息 3)任何重要数据。简短回答。"

for img in "$IMAGES_DIR"/*.jpg "$IMAGES_DIR"/*.png; do
    [ -f "$img" ] || continue
    fname=$(basename "$img")
    fsize=$(du -h "$img" | cut -f1)
    b64=$(base64 -w 0 "$img")
    
    echo "════════════════════════════════════════"
    echo "📸 分析: $fname ($fsize)"
    echo "════════════════════════════════════════"
    
    start_ts=$(date +%s%N)
    resp=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        -d "$(jq -n --arg b64 "$b64" --arg prompt "$PROMPT" '{
            model: "qwen3.6-35b",
            max_tokens: 1024,
            messages: [{
                role: "user",
                content: [
                    {type: "image_url", image_url: {url: ("data:image/jpeg;base64," + $b64)}},
                    {type: "text", text: $prompt}
                ]
            }]
        }')")
    
    end_ts=$(date +%s%N)
    elapsed=$(( (end_ts - start_ts) / 1000000 ))
    
    # 尝试提取 content 或 reasoning
    content=$(echo "$resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
choices = d.get('choices', [{}])
if choices:
    msg = choices[0].get('message', {})
    c = msg.get('content', '') or msg.get('reasoning', '')
    print(c[:500] if c else 'No content')
else:
    print('No choices')
" 2>/dev/null)
    
    echo "$content"
    echo "(耗时: ${elapsed}ms)"
    echo ""
done
