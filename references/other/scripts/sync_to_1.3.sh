#!/bin/bash
# 同步配置到 192.168.1.3

TARGET_HOST="192.168.1.3"
TARGET_USER="chen"
TARGET_PATH="/home/chen/.openclaw"

# 1. 同步 openclaw.json 配置
echo "同步 openclaw.json..."
scp /root/.openclaw/openclaw.json $TARGET_USER@$TARGET_HOST:$TARGET_PATH/

# 2. 同步 workspace 目录
echo "同步 workspace 目录..."
rsync -avz --exclude='node_modules' --exclude='.git' /root/.openclaw/workspace/ $TARGET_USER@$TARGET_HOST:$TARGET_PATH/workspace/

echo "同步完成！"

# 3. 检查红茶服务状态
echo "检查红茶服务状态..."
ssh $TARGET_USER@$TARGET_HOST "systemctl status openclaw-gateway"

# 4. 重启红茶服务（如果需要）
echo "重启红茶服务..."
ssh $TARGET_USER@$TARGET_HOST "systemctl restart openclaw-gateway"

echo "同步和重启完成！"