#!/bin/bash
# ComputeHub 自升级脚本
# 用法: bash self-upgrade.sh
# 通过 Gateway task 机制让 worker 远程升级自身

set -e

GW="http://localhost:8282"
NODE_ID="ecs-p2ph"
TASK_PREFIX="selfupgrade-$(date +%s)"

# 步骤 1: 下载新二进制并验证
echo "📥 步骤 1: 下载新二进制..."
curl -sL -o /tmp/computehub-new \
  "https://github.com/openclawlab/computehub/releases/download/v0.7.10/computehub-linux-arm64" \
  --connect-timeout 30 --max-time 120

if [ ! -f /tmp/computehub-new ] || [ ! -s /tmp/computehub-new ]; then
  echo "❌ 下载失败，文件为空"
  exit 1
fi

chmod +x /tmp/computehub-new
SIZE=$(stat -c%s /tmp/computehub-new)
echo "   ✅ 下载完成: $(ls -lh /tmp/computehub-new | awk '{print $5}')"
echo "   ✅ 可执行: yes"
echo "   ✅ 大小: $SIZE bytes"

# 步骤 2: 通过 task 检查 worker 健康
echo ""
echo "🩺 步骤 2: 检查 worker 健康..."
HEALTH_JSON=$(curl -s --max-time 5 "$GW/api/v1/nodes" 2>&1)
if echo "$HEALTH_JSON" | grep -q "$NODE_ID"; then
  echo "   ✅ worker $NODE_ID 在线"
else
  echo "   ⚠️ 节点 $NODE_ID 的节点信息:"
  echo "$HEALTH_JSON" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_JSON"
fi

# 步骤 3: 提交新二进制到 Gateway 本地存储 (如果 API 支持)
# 否则直接复制到目标路径
echo ""
echo "📋 步骤 3: 部署新二进制..."

# 提交一个 task 来停掉旧的进程
UPGRADE_TASK_ID="${TASK_PREFIX}-upgrade"
echo "   📤 提交升级任务: $UPGRADE_TASK_ID"

# 这个 task 会: 拷贝新二进制, 停旧进程, 启动新进程
UPGRADE_SCRIPT=$(cat <<'SCRIPT'
#!/bin/bash
# 在 worker 上执行的实际升级
cp /tmp/computehub-new /home/computehub/computehub
chmod +x /home/computehub/computehub
echo "BINARY_COPIED_OK"

# 停掉旧 worker 和 gateway
pkill -f "computehub worker"
sleep 2
pkill -f "computehub gateway"
sleep 2

# 验证旧进程已停
if pgrep -f "computehub" > /dev/null; then
  echo "WARNING: some computehub processes still running, force kill"
  pkill -9 -f "computehub"
  sleep 1
fi

# 启动新 gateway
cd /home/computehub
nohup ./computehub gateway --port 8282 > gateway.log 2>&1 &
echo "GATEWAY_STARTED"

# 等待 gateway 就绪
for i in $(seq 1 10); do
  if curl -s --max-time 2 http://localhost:8282/api/v1/nodes >/dev/null 2>&1; then
    echo "GATEWAY_READY"
    break
  fi
  sleep 1
done

# 启动新 worker
nohup ./computehub worker --gw http://localhost:8282 --node-id ecs-p2ph --interval 3 --concurrent 8 --heartbeat 10 > worker.log 2>&1 &
echo "WORKER_STARTED"

# 最终验证
sleep 2
VERSION=$(./computehub version 2>/dev/null || echo "no-version")
echo "VERSION_CHECK: $VERSION"
PROCS=$(ps aux | grep "computehub" | grep -v grep)
echo "PROCESSES:"
echo "$PROCS"
SCRIPT

# 提交 task
RESPONSE=$(curl -s --max-time 10 -X POST "$GW/api/v1/tasks/submit" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json
script = '''$UPGRADE_SCRIPT'''
print(json.dumps({
    'task_id': '$UPGRADE_TASK_ID',
    'command': script,
    'timeout': 60
}))
")" 2>&1)

echo "   提交响应: $RESPONSE"
echo ""

# 步骤 4: 轮询等待升级完成
echo "👀 步骤 4: 等待升级任务完成..."
for i in $(seq 1 30); do
  sleep 2
  DETAIL=$(curl -s --max-time 5 "$GW/api/v1/tasks/detail?task_id=$UPGRADE_TASK_ID&node_id=$NODE_ID" 2>&1)
  STATUS=$(echo "$DETAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
  
  if [ "$STATUS" = "completed" ]; then
    echo "   ✅ 升级完成!"
    echo "$DETAIL" | python3 -m json.tool 2>/dev/null | head -20
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "   ❌ 升级失败"
    echo "$DETAIL" | python3 -m json.tool 2>/dev/null
    exit 1
  fi
  
  echo "   等待中... (第 $i 次轮询, 状态: $STATUS)"
done

# 步骤 5: 最终验证
echo ""
echo "🔍 步骤 5: 验证升级结果"
sleep 3

# 检查新 gateway
if curl -s --max-time 5 "$GW/api/v1/nodes" >/dev/null 2>&1; then
  NODES=$(curl -s --max-time 5 "$GW/api/v1/nodes" 2>&1)
  echo "   ✅ Gateway 正常响应"
  echo "   节点信息: $NODES" | head -5
else
  echo "   ⚠️ Gateway 可能需要重新检查（升级过程中已重启）"
fi

echo ""
echo "🎉 自升级流程完成!"
echo "如果 Gateway 重启导致连接断开, 请在终端重新连接"
