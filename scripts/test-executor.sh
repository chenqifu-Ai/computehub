#!/bin/bash
# ComputeHub v3.0 - 执行器测试
set -e
echo "=== 🧪 Executor Tests ==="
CGO_ENABLED=0 go test -v -count=1 ./src/executor/...
echo "✅ Executor tests passed"
