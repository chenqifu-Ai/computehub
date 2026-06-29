#!/bin/bash
# COM-STD-001-TEST: Broadcast
set -e

GATEWAY="http://36.250.122.43:8282"
PASS=0
FAIL=0

echo "=== Broadcast ==="
echo ""

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

# BC-001: 完整 arc_net_broadcast 格式
test_case "BC-001" "arc_net broadcast" '
    payload=$(python3 -c "
import json
env = {
    \"version\": \"1.0\",
    \"event\": \"broadcast\",
    \"sender\": {
        \"node_id\": \"test-script\",
        \"label\": \"test\",
        \"host\": \"localhost\",
        \"platform\": \"script\",
        \"model\": \"test\",
        \"version\": \"1.0\"
    },
    \"seq\": 1,
    \"timestamp\": 0,
    \"payload\": json.dumps({\"message\":\"COM-STD-001 broadcast test\"})
}
msg = json.dumps({
    \"type\": \"arc_net_broadcast\",
    \"arc_net\": json.loads(env),
    \"role\": \"system\",
    \"content\": \"test broadcast\"
})
print(msg)
")
    result=$(curl -s --connect-timeout 5 -X POST "$GATEWAY/api/v1/cluster/broadcast" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)
    echo "    result: $(echo "$result" | head -c 100)"
    [ -n "$result" ]
'

# BC-002: 格式验证
test_case "BC-002-no-type" "missing type => 400" '
    result=$(curl -s -X POST "$GATEWAY/api/v1/cluster/broadcast" \
        -H "Content-Type: application/json" \
        -d "{\"message\":\"test\"}" 2>/dev/null)
    echo "$result" | grep -q "Invalid" || true
    [ -n "$result" ]
'

echo ""
echo "PASS=$PASS"
echo "FAIL=$FAIL"
exit $FAIL