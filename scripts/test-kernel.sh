#!/bin/bash
# ComputeHub v3.0 - 内核测试
set -e

echo "=== 🔬 Kernel Unit Tests ==="
CGO_ENABLED=0 go test -v -count=1 ./src/kernel/...
echo "✅ Kernel tests passed"
