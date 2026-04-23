#!/bin/bash
# ComputeHub v3.0 - 基因系统测试
set -e
echo "=== 🧪 Gene System Tests ==="
CGO_ENABLED=0 go test -v -count=1 ./src/gene/...
echo "✅ Gene tests passed"
