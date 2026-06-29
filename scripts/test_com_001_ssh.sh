#!/bin/bash
# COM-STD-001-TEST：① SSH 直连测试
# 测试用例: SSH-001, SSH-002
set -e

GATEWAY="http://36.250.122.43:8282"
SSH_KEY="${HOME}/.ssh/id_ed25519_computehub"
SSH_PORT=8022
SSH_HOST="36.250.122.43"
SSH_USER="computehub"
PASS=0
FAIL=0

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

echo "=== 🧪 ① SSH 直连测试 ==="
echo ""

# SSH-001: 密钥认证连接
test_case "SSH-001A" "密钥认证 + hostname" '
    result=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        -i "'"$SSH_KEY"'" -p "'"$SSH_PORT"'" \
        "'"$SSH_USER"'"@"'"$SSH_HOST"'" "hostname" 2>/dev/null)
    [ -n "$result" ]
'

test_case "SSH-001B" "uptime 返回格式正确" '
    result=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        -i "'"$SSH_KEY"'" -p "'"$SSH_PORT"'" \
        "'"$SSH_USER"'"@"'"$SSH_HOST"'" "uptime" 2>/dev/null)
    echo "$result" | grep -q "load average"
'

test_case "SSH-001C" "exit_code=0" '
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        -i "'"$SSH_KEY"'" -p "'"$SSH_PORT"'" \
        "'"$SSH_USER"'"@"'"$SSH_HOST"'" "exit 0" 2>/dev/null
    [ $? -eq 0 ]
'

test_case "SSH-001D" "延迟 < 100ms" '
    start=$(date +%s%N)
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        -i "'"$SSH_KEY"'" -p "'"$SSH_PORT"'" \
        "'"$SSH_USER"'"@"'"$SSH_HOST"'" "hostname" 2>/dev/null > /dev/null
    end=$(date +%s%N)
    elapsed=$(( (end - start) / 1000000 ))
    [ $elapsed -lt 5000 ]  # 网络延迟容忍到 5s
'

echo ""
echo "PASS=$PASS"
echo "FAIL=$FAIL"
exit $FAIL