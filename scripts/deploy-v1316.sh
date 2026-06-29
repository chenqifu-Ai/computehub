#!/bin/bash
# Deploy v1.3.16 to all remote nodes
# Each node downloads and replaces its binary

GATEWAY="http://36.250.122.43:8282"
FILE_URL="$GATEWAY/api/v1/files"

echo "🚀 ComputingHub v1.3.16 全节点部署"
echo "=================================="

# ECS node - uses Gateway's file service to download
echo ""
echo "🐧 ECS 节点 (36.250.122.43):"
echo "  1. 停旧进程: kill -9 \$(pgrep -f 'computehub.*worker')"
echo "  2. 下载: wget -O computehub $FILE_URL/computehub-linux-amd64"
echo "  3. 启动: nohup ./computehub worker --gw $GATEWAY --node-id ecs-p2ph"

echo ""
echo "🪟 Windows 节点 (100.115.160.10):"
echo "  1. 停旧进程: Get-Process computehub | Stop-Process -Force"
echo "  2. 下载: curl -o computehub.exe $FILE_URL/computehub-windows-amd64.exe"
echo "  3. 启动: .\\computehub.exe worker --gw $GATEWAY --node-id windows-mobile"

echo ""
echo "💡 在 Gateway 上用 curl 测试下载:"
echo "  curl -o test-amd64 $FILE_URL/computehub-linux-amd64"
echo "  curl -o test-win.exe $FILE_URL/computehub-windows-amd64.exe"
