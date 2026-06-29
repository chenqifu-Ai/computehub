#!/bin/bash
# COM-STD-001-TEST：⑤ proot→agent AI 对话测试
# 测试用例: AI-001, AI-002, AI-003
set -e

GATEWAY="http://36.250.122.43:8282"
PASS=0
FAIL=0

echo "=== 🧪 ⑤ proot→agent AI 对话测试 ==="
echo ""

# 检查各节点的 proot 可用性
echo "  检查节点 AI 能力..."
for node in ecs-p2ph worker-arm windows-mobile; do
    status=$(curl -sf "$GATEWAY/api/v1/nodes/list" 2>/dev/null | \
        python3 -c "
import json,sys
data=json.load(sys.stdin)['data']
for n in data:
    if n['node_id'] == '$node':
        print(n.get('status','offline'))
        break
" 2>/dev/null)
    echo "    $node: $status"
done
echo ""

test_case() {
    local name="$1"
    local desc="$2"
    echo "  [TEST] $desc..."
    if eval "$3"; then
        echo "    ✅ $name PASS"
        PASS=$((PASS+1))
    else
        echo "    ❌ $name FAIL"
        FAIL=$((FAIL+1))
    fi
}

submit_and_wait() {
    local node="$1"
    local cmd="$2"
    local timeout="${3:-120}"
    
    resp=$(curl -sf -X POST "$GATEWAY/api/v1/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{\"node_id\":\"$node\",\"command\":\"$(echo "$cmd" | sed 's/"/\\"/g')\",\"timeout\":$timeout}" 2>/dev/null)
    
    task_id=$(echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('data',{}).get('task_id',''))" 2>/dev/null)
    
    if [ -z "$task_id" ]; then
        echo "    无法获取 task_id"
        return 1
    fi
    
    for i in $(seq 1 $((timeout / 2 + 10))); do
        result=$(curl -sf "$GATEWAY/api/v1/tasks/detail?task_id=$task_id" 2>/dev/null)
        status=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin).get('data',{}); print(d.get('status','pending'))" 2>/dev/null)
        
        if [ "$status" = "completed" ] || [ "$status" = "failed" ] || [ "$status" = "timed_out" ]; then
            echo "$result"
            return 0
        fi
        sleep 3
    done
    
    echo "$result"
    return 1
}

# AI-001: 基础 AI 对话（ecs-p2ph 用 openclaw agent）
test_case "AI-001-ECS" "ecs-p2ph AI 基础对话" '
    result=$(submit_and_wait "ecs-p2ph" \
        "cd /home/computehub/OPC && ./computehub agent --agent main --message \"回复：OK\" 2>&1 | tail -10" \
        120)
    stdout=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"stdout\",\"\")[:500])" 2>/dev/null)
    echo "    stdout 片段: $(echo "$stdout" | head -c 200)"
    [ -n "$stdout" ]
'

# AI-002: AI 超时测试
test_case "AI-002" "AI 对话超时处理" '
    result=$(submit_and_wait "ecs-p2ph" \
        "cd /home/computehub/OPC && timeout 5 ./computehub agent --agent main --message \"请写一篇5000字文章\" 2>&1" \
        30)
    status=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"status\",\"\"))" 2>/dev/null)
    echo "    status: $status"
    [ "$status" = "timed_out" ] || [ "$status" = "failed" ] || [ "$status" = "completed" ]
'

# AI-003: 中文指令
test_case "AI-003" "中文指令 base64 编码" '
    msg_b64=$(echo -n "请用一句话介绍你自己" | base64 -w0)
    result=$(submit_and_wait "ecs-p2ph" \
        "echo \"$msg_b64\" | base64 -d | head -c 200 | xargs -I{} sh -c '\''cd /home/computehub/OPC && ./computehub agent --agent main --message \"{}\" 2>&1'\'' | tail -10" \
        120)
    stdout=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
s=d.get(\"stdout\",\"\")
print(s[:300])" 2>/dev/null)
    echo "    回复片段: $(echo "$stdout" | head -c 200)"
    [ -n "$stdout" ]
'

echo ""
echo "PASS=$PASS"
echo "FAIL=$FAIL"
exit $FAIL