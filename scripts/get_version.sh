#!/bin/bash
# get_version.sh — 版本号统一来源
# 用法: VERSION=$(bash scripts/get_version.sh)
# 所有需要版本号的脚本 source 这个文件即可：
#   VERSION=$(cd "$(dirname "$0")" && bash ./get_version.sh)

# 版本号统一来源：git tag 最新版本
V=$(git tag -l | grep -E '^v?[0-9]+\.' | sort -V | tail -1 | sed 's/^v//')
if [ -z "$V" ]; then
    V=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
fi
echo "$V"
