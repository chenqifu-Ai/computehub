#!/bin/bash
# ComputeHub v3.0 - 纯化流水线测试
set -e
echo "=== 🧪 Pure Pipeline Tests ==="
CGO_ENABLED=0 go test -v -count=1 ./src/pure/...
echo "✅ Pure tests passed"
