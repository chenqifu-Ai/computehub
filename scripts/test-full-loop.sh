#!/bin/bash
# ComputeHub v3.0 - 全链路集成测试
set -e

echo "🔗 === Full-Loop Integration Test ==="
echo ""

# Build first
echo "🔨 Building..."
CGO_ENABLED=0 go build -trimpath -mod=readonly -o /tmp/ch-gateway main.go 2>&1

echo "🧪 Running all module tests..."
CGO_ENABLED=0 go test -count=1 ./src/kernel/... ./src/pure/... ./src/executor/... ./src/gene/... ./src/gateway/... 2>&1

echo ""
echo "========================================="
echo "✅ Full-Loop Integration Test PASSED"
echo "========================================="
echo "  Kernel:     ✅"
echo "  Pipeline:   ✅"
echo "  Executor:   ✅"
echo "  Gene:       ✅"
echo "  Gateway:    ✅"
echo "========================================="
