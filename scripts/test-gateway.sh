#!/bin/bash
# ComputeHub v3.0 - 网关测试
set -e
echo "=== 🧪 Gateway API Tests ==="
CGO_ENABLED=0 go test -v -count=1 ./src/gateway/...
echo "✅ Gateway tests passed"
