#!/bin/bash
# COM-STD-001-TEST：E2E 全链路测试
# 用例: E2E-001, E2E-002, E2E-003
set -e

GATEWAY="http://36.250.122.43:8282"
PASS=0
FAIL=0

echo "=== 🧪 E2E 全链路测试 ==="
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

# 获取在线节点
online_nodes() {
    curl -sf "$GATEWAY/api/v1/nodes/list" 2>/dev/null | \
        python3 -c "
import json,sys
data=json.load(sys.stdin)['data']
online=[n['node_id'] for n in data if n['status']=='online']
print(' '.join(online))
" 2>/dev/null
}

NODES=$(online_nodes)
echo "   在线节点: $NODES"

submit_and_wait() {
    local node="$1"
    local cmd="$2"
    local timeout="${3:-60}"
    
    resp=$(curl -sf -X POST "$GATEWAY/api/v1/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{\"node_id\":\"$node\",\"command\":\"$(echo "$cmd" | sed 's/"/\\"/g')\",\"timeout\":$timeout}" 2>/dev/null)
    
    task_id=$(echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('data',{}).get('task_id',''))" 2>/dev/null)
    
    if [ -z "$task_id" ]; then
        echo "    ❌ 无法获取 task_id"
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

# E2E-001: 跨节点 AI 对话全链路
test_case "E2E-001" "跨节点 AI 对话（端智 → ecs-p2ph → LLM）" '
    result=$(submit_and_wait "ecs-p2ph" \
        "cd /home/computehub/OPC && ./computehub agent --agent main --message \"请用中文回复：COM-STD-001 全链路测试通过\" 2>&1 | tail -10" \
        120)
    status=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"status\",\"\"))" 2>/dev/null)
    echo "    status: $status"
    [ "$status" = "completed" ]
'

# E2E-002: 三节点同时查询
if [ -n "$NODES" ]; then
    e2e002_pass=true
    
    for node in $NODES; do
        result=$(submit_and_wait "$node" "hostname && date +%s" 30)
        status=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"status\",\"\"))" 2>/dev/null)
        
        if [ "$status" != "completed" ]; then
            echo "    ❌ $node 响应失败 (status=$status)"
            e2e002_pass=false
        else
            echo "    ✅ $node 响应成功"
        fi
    done
    
    test_case "E2E-002" "多节点同时查询" '$e2e002_pass'
fi

# E2E-003: 广播 + 确认
test_case "E2E-003" "广播消息" '
    result=$(curl -sf -X POST "$GATEWAY/api/v1/cluster/broadcast" \
        -H "Content-Type: application/json" \
        -d "{\"message\":\"E2E-003 全链路广播测试\",\"source\":\"e2e-test\",\"severity\":\"info\"}" 2>/dev/null)
    success=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get(\"success\",False))" 2>/dev/null)
    echo "    广播结果: $success"
    [ "$success" = "True" ]
'

echo ""
echo "PASS=$PASS"
echo "FAIL=$FAIL"
exit $FAIL