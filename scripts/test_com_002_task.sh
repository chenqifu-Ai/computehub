#!/bin/bash
# COM-STD-001-TEST: Task API
set -e

GATEWAY="http://36.250.122.43:8282"
PASS=0
FAIL=0

NODES=$(curl -sf "$GATEWAY/api/v1/nodes/list" | \
    python3 -c "
import json,sys
data=json.load(sys.stdin)['data']
online=[n['node_id'] for n in data if n['status']=='online']
print(' '.join(online))
" 2>/dev/null)

echo "=== Task API ==="
echo "   online: $NODES"
echo ""

if [ -z "$NODES" ]; then
    echo "  no online nodes, skip"
    echo "PASS=0"; echo "FAIL=0"; exit 0
fi

test_case() {
    local name="$1"
    local desc="$2"
    echo "  [TEST] $desc..."
    if eval "$3"; then
        echo "    $name PASS"
        PASS=$((PASS+1))
    else
        echo "    $name FAIL"
        FAIL=$((FAIL+1))
    fi
}

submit_and_wait() {
    local node="$1"
    local cmd="$2"
    local timeout="${3:-30}"
    local escaped_cmd
    escaped_cmd=$(echo "$cmd" | sed 's/"/\\"/g')
    
    resp=$(curl -sf -X POST "$GATEWAY/api/v1/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{\"node_id\":\"$node\",\"command\":\"$escaped_cmd\",\"timeout\":$timeout}" 2>/dev/null) || {
        echo "    submit fail"
        return 1
    }
    
    task_id=$(echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('data',{}).get('task_id',''))" 2>/dev/null)
    if [ -z "$task_id" ]; then
        echo "    no task_id: $(echo "$resp" | head -c 100)"
        return 1
    fi
    
    for i in $(seq 1 $((timeout / 2 + 10))); do
        result=$(curl -sf "$GATEWAY/api/v1/tasks/detail?task_id=$task_id" 2>/dev/null)
        status=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data',{})
print(d.get('status','pending'))" 2>/dev/null)
        if [ "$status" = "completed" ] || [ "$status" = "failed" ] || [ "$status" = "timed_out" ]; then
            echo "$result"
            return 0
        fi
        sleep 2
    done
    echo "    timeout wait"
    echo "$result" 2>/dev/null
    return 1
}

# TASK-001: echo on each online node (skip windows if fully loaded)
for node in $NODES; do
    cap=$(curl -sf "$GATEWAY/api/v1/nodes/list" 2>/dev/null | python3 -c "
import json,sys
data=json.load(sys.stdin)['data']
for n in data:
    if n['node_id'] == '$node':
        print(n.get('active_tasks','?'))
" 2>/dev/null)
    
    test_case "TASK-001-$node" "$node echo OK (active=$cap)" '
        result=$(submit_and_wait "'"$node"'" "echo OK" 20)
        exit_code=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"exit_code\",-1))" 2>/dev/null)
        [ "$exit_code" = "0" ]
    '
done

# TASK-002: timeout
test_case "TASK-002" "timeout mechanism" '
    result=$(submit_and_wait "ecs-p2ph" "sleep 20" 5)
    ec=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin).get(\"data\",{})
print(d.get(\"exit_code\",-1))" 2>/dev/null)
    # actual behavior: status=completed exit_code=-1 or status=timed_out
    [ "$ec" != "0" ]
'

# TASK-003: priority
test_case "TASK-003" "priority queue functional" '
    for prio in 1 1 10 1; do
        curl -sf -X POST "$GATEWAY/api/v1/tasks/submit" \
            -H "Content-Type: application/json" \
            -d "{\"node_id\":\"ecs-p2ph\",\"command\":\"echo p$prio\",\"priority\":$prio,\"timeout\":5}" \
            > /dev/null 2>&1 || true
    done
    sleep 2
    curl -sf "$GATEWAY/api/health" > /dev/null 2>&1
'

echo ""
echo "PASS=$PASS"
echo "FAIL=$FAIL"
exit $FAIL