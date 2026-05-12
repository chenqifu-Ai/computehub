#!/bin/bash
# start-gateway.sh — 启动、重启 ComputeHub Gateway
# 用法: start-gateway.sh                 （启动）
#        start-gateway.sh restart        （重启）
#        start-gateway.sh stop           （停止）

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) PLAT="linux-arm64" ;;
  x86_64|amd64)  PLAT="linux-amd64" ;;
  *) echo "❌ 未知架构: $ARCH"; exit 1 ;;
esac

# 找最新版本的二进制（优先 versioned 目录，再回退到根目录）
VERSION=$(cat deploy/version.txt 2>/dev/null || echo "0.0.0")
GW_BIN=""
for candidate in \
  "deploy/${VERSION}/${PLAT}/computehub-gateway" \
  "deploy/${VERSION}/computehub-gateway-${PLAT}" \
  "deploy/computehub-gateway-${PLAT}"; do
  if [ -f "$candidate" ]; then
    GW_BIN="$candidate"
    break
  fi
done

if [ -z "$GW_BIN" ]; then
  echo "❌ 找不到 computehub-gateway 二进制"
  echo "   查找路径: deploy/${VERSION}/${PLAT}/computehub-gateway"
  exit 1
fi

echo "🔍 版本: v${VERSION}, 架构: ${PLAT}"
echo "📦 二进制: ${GW_BIN}"

CMD="${1:-start}"
case "$CMD" in
  stop)
    echo "🛑 停止 Gateway..."
    pkill -f "computehub-gateway" 2>/dev/null || true
    fuser -k 8282/tcp 2>/dev/null || true
    sleep 1
    echo "✅ 已停止"
    exit 0
    ;;
  restart)
    echo "🔄 重启 Gateway..."
    pkill -f "computehub-gateway" 2>/dev/null || true
    fuser -k 8282/tcp 2>/dev/null || true
    sleep 1
    ;;
  start)
    # 检查是否已在运行
    if pgrep -f "computehub-gateway" > /dev/null 2>&1; then
      echo "✅ Gateway 已在运行 (PID: $(pgrep -f computehub-gateway | head -1))"
      echo "   要重启: $0 restart"
      exit 0
    fi
    ;;
esac

# 启动
echo "🚀 启动 Gateway..."
nohup "$GW_BIN" > /tmp/gateway.log 2>&1 &
GW_PID=$!
echo "   PID: ${GW_PID}"

# 等待就绪
for i in $(seq 1 10); do
  sleep 1
  if curl -s "http://localhost:8282/api/health" > /dev/null 2>&1; then
    echo "✅ Gateway 启动成功 (${i}s)"
    echo "   📍 http://localhost:8282"
    echo "   📋 /tmp/gateway.log"
    exit 0
  fi
done

echo "❌ Gateway 启动超时，请检查日志: /tmp/gateway.log"
exit 1
