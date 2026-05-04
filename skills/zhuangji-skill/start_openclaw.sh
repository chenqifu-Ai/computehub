#!/bin/bash
# OpenClaw启动脚本 - 目标: 192.168.1.19

TARGET_HOST="192.168.1.19"
TARGET_PORT="8022"
TARGET_USER="u0_a213"
TARGET_PASS="123"
DEPLOY_PORT="18789"

# 启动OpenClaw Gateway
sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o GlobalKnownHostsFile=/dev/null -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
    "pkill -f 'openclaw' || true && openclaw gateway --port $DEPLOY_PORT &"

echo "OpenClaw Gateway启动完成"
echo "访问地址: http://$TARGET_HOST:$DEPLOY_PORT"
echo "健康检查: http://$TARGET_HOST:$DEPLOY_PORT/health"