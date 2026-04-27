#!/bin/bash
# Kernel 测试
set -e
cd "$(dirname "$0")/src"
CGO_ENABLED=0 go test -v -run "TestKernel" ./kernel/ -timeout 30s 2>&1
