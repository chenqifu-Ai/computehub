#!/bin/bash
# ComputeHub M0 工程规范化 - 测试套件
# 运行所有模块的测试并报告覆盖情况

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0
TIMEOUT=30s

log() { echo "[$(date "+%H:%M:%S")] $*"; }

run_test() {
    local name=$1
    local pkg=$2
    log "🧪 Testing ${name}..."
    if CGO_ENABLED=0 go test -count=1 -timeout ${TIMEOUT} "${PROJECT_DIR}/src/${pkg}" 2>/dev/null; then
        log "✅ ${name} passed"
        PASS=$((PASS + 1))
    else
        log "❌ ${name} FAILED"
        FAIL=$((FAIL + 1))
    fi
}

run_test "Blockchain"  "blockchain"
run_test "Executor"    "executor"
run_test "Gateway"     "gateway"
run_test "Gene"        "gene"
run_test "Kernel"      "kernel"
run_test "Node"        "node"
run_test "Pure"        "pure"
run_test "Scheduler"   "scheduler"

echo ""
echo "═══════════════════════════════════"
echo "  📊 ${PASS}/$((PASS+FAIL)) passed (${FAIL} failed)"
echo "═══════════════════════════════════"
exit ${FAIL}
