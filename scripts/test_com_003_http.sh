#!/bin/bash
# COM-STD-001-TEST: Gateway HTTP API
set -e

GATEWAY="http://36.250.122.43:8282"
PASS=0
FAIL=0

echo "=== Gateway HTTP API ==="
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

# health
test_case "health-200" "/api/health -> 200" '
    s=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/health" 2>/dev/null)
    [ "$s" = "200" ]
'

# status kernel
test_case "status-kernel" "/api/status kernel=RUNNING" '
    s=$(curl -sf "$GATEWAY/api/status" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\"kernel\",{}).get(\"status\",\"\"))" 2>/dev/null)
    [ "$s" = "RUNNING" ]
'

# nodes list
test_case "nodes-list" "/api/v1/nodes/list >=1 node" '
    n=$(curl -sf "$GATEWAY/api/v1/nodes/list" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get(\"data\",[])))" 2>/dev/null)
    [ "$n" -ge 1 ] 2>/dev/null
'

# agents list
test_case "agents-list" "/api/v1/agents/list -> 200" '
    s=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/v1/agents/list" 2>/dev/null)
    [ "$s" = "200" ]
'

# 404
test_case "404" "error path -> 404" '
    s=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/nonexistent" 2>/dev/null)
    [ "$s" = "404" ]
'

echo ""
echo "PASS=$PASS"
echo "FAIL=$FAIL"
exit $FAIL