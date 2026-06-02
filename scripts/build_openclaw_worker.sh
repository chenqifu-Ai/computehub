#!/bin/bash
# ============================================================
# build_openclaw_worker.sh
# 在 ecs-p2ph (36.250.122.43) 上从源码编译 OpenClaw
# 指定 commit: 61d171a (2026-03-14 "fix browser batch dispatch")
# ============================================================
set -e

REMOTE="computehub@36.250.122.43"
IDENTITY="~/.ssh/id_ed25519_computehub"
PORT=8022
SSH_CMD="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -i $IDENTITY $REMOTE -p $PORT"

echo "🔨 第1步: 在 ECS 上克隆 OpenClaw 源码到 /home/computehub/openclaw"
$SSH_CMD << 'SCRIPT'
set -e
cd /home/computehub

# 如果已存在则直接使用
if [ -d "openclaw/.git" ]; then
  echo "📦 仓库已存在，更新中..."
  cd openclaw
  git fetch origin
  git reset --hard HEAD
else
  echo "📦 克隆仓库..."
  git clone https://github.com/openclaw/openclaw.git
  cd openclaw
fi

# 切换到指定 commit
echo "🔍 切换到 commit 61d171a..."
git checkout 61d171a
echo "✅ 当前 commit: $(git log --oneline -1)"
SCRIPT

echo "🔨 第2步: 编译 OpenClaw (linux amd64)"
$SSH_CMD << 'SCRIPT'
set -e
cd /home/computehub/openclaw

# 确保 Go 模块
echo "📦 go mod tidy..."
go mod tidy

echo "🏗️ 编译 openclaw 二进制..."
go build -ldflags="-s -w" -o /home/computehub/openclaw-binary .

echo "✅ 编译完成"
ls -lh /home/computehub/openclaw-binary
file /home/computehub/openclaw-binary
SCRIPT

echo "🔨 第3步: 安装 OpenClaw 到系统"
$SSH_CMD << 'SCRIPT'
set -e
BINARY="/home/computehub/openclaw-binary"

echo "📋 验证二进制..."
$BINARY version 2>&1 || echo "⚠️ version command not available yet (need config)"

echo "📋 复制到 /usr/local/bin..."
sudo cp $BINARY /usr/local/bin/openclaw
sudo chmod +x /usr/local/bin/openclaw

echo "✅ 验证..."
which openclaw
openclaw version 2>&1 || echo "⚠️ openclaw version 需要配置文件才能显示"
SCRIPT

echo "🔨 第4步: 停止旧 worker，用新二进制启动"
$SSH_CMD << 'SCRIPT'
set -e
cd /home/computehub

echo "🛑 停止旧进程..."
sudo systemctl stop openclaw 2>/dev/null || true
pkill -f "openclaw worker" 2>/dev/null || true
pkill -f "openclaw gateway" 2>/dev/null || true
sleep 1

echo "🚀 启动新 worker..."
# 如果已有 gw 进程在运行，只启动 worker
if pgrep -f "computehub gateway" > /dev/null 2>&1; then
  echo "📡 连接已有 gateway..."
  nohup /usr/local/bin/openclaw worker \
    --gw http://localhost:8282 \
    --node-id ecs-p2ph \
    --interval 3 \
    --concurrent 8 \
    --heartbeat 10 \
    > worker_openclaw.log 2>&1 &
  echo "✅ Worker PID: $!"
else
  echo "📡 启动 gateway + worker..."
  nohup /usr/local/bin/openclaw gateway \
    > gateway_openclaw.log 2>&1 &
  sleep 2
  nohup /usr/local/bin/openclaw worker \
    --gw http://localhost:8282 \
    --node-id ecs-p2ph \
    --interval 3 \
    --concurrent 8 \
    --heartbeat 10 \
    > worker_openclaw.log 2>&1 &
  echo "✅ Gateway PID: $(pgrep -f 'openclaw gateway' | head -1)"
  echo "✅ Worker PID: $(pgrep -f 'openclaw worker' | head -1)"
fi
SCRIPT

echo ""
echo "🎉 完成！查看进程状态:"
$SSH_CMD "ps aux | grep -E 'openclaw|computehub' | grep -v grep"
