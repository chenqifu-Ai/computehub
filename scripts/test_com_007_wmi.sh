#!/bin/bash
# COM-STD-001-TEST：⑦ WMI 测试 (Windows)
# 测试用例: WMI-001, WMI-002
set -e

GATEWAY="http://36.250.122.43:8282"
PASS=0
FAIL=0

echo "=== 🧪 ⑦ WMI 测试 ==="
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
    local timeout="${3:-30}"
    
    resp=$(curl -sf -X POST "$GATEWAY/api/v1/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{\"node_id\":\"$node\",\"command\":\"$(echo "$cmd" | sed 's/"/\\"/g')\",\"timeout\":$timeout}" 2>/dev/null)
    
    task_id=$(echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('data',{}).get('task_id',''))" 2>/dev/null)
    
    if [ -z "$task_id" ]; then
        echo "    无法获取 task_id"
        return 1
    fi
    
    for i in $(seq 1 $((timeout / 2 + 5))); do
        result=$(curl -sf "$GATEWAY/api/v1/tasks/detail?task_id=$task_id" 2>/dev/null)
        status=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin).get('data',{}); print(d.get('status','pending'))" 2>/dev/null)
        
        if [ "$status" = "completed" ] || [ "$status" = "failed" ] || [ "$status" = "timed_out" ]; then
            echo "$result"
            return 0
        fi
        sleep 2
    done
    
    echo "$result"
    return 1
}

# 检查 windows-mobile 是否在线
win_status=$(curl -sf "$GATEWAY/api/v1/nodes/list" 2>/dev/null | \
    python3 -c "
import json,sys
data=json.load(sys.stdin)['data']
for n in data:
    if n['node_id'] == 'windows-mobile':
        print(n.get('status','offline'))
        break
" 2>/dev/null)

echo "    windows-mobile 状态: $win_status"

if [ "$win_status" = "online" ]; then
    # WMI-001: Windows 节点 WMI 查询
    test_case "WMI-001" "Windows 执行 wmic 查询" '
        result=$(submit_and_wait "windows-mobile" "wmic os get caption" 30)
        stdout=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"stdout\",\"\")[:200])" 2>/dev/null)
        exit_code=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"exit_code\",-1))" 2>/dev/null)
        echo "    stdout: $(echo "$stdout" | head -c 100)"
        [ "$exit_code" = "0" ]
    '
else
    echo "  ⚠️ windows-mobile 离线，跳过 WMI-001"
fi

# WMI-002: Linux 节点 WMI 不可用
for node in ecs-p2ph worker-arm; do
    test_case "WMI-002-$node" "$node 执行 wmic 应失败" '
        result=$(submit_and_wait "'"$node"'" "wmic os get caption" 15)
        exit_code=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"exit_code\",-1))" 2>/dev/null)
        stdout=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"stdout\",\"\")[:100])" 2>/dev/null)
        echo "    exit_code: $exit_code"
        [ "$exit_code" != "0" ]
    '
done

echo ""
echo "PASS=$PASS"
echo "FAIL=$FAIL"
exit $FAIL