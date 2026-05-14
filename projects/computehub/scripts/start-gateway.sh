#!/bin/bash
# start-gateway.sh — 启动、重启 ComputeHub Gateway（三合一版本）
# 用法: start-gateway.sh                 （启动）
#        start-gateway.sh restart        （重启）
#        start-gateway.sh stop           （停止）
#        start-gateway.sh status         （状态）

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) PLAT="linux-arm64" ;;
  x86_64|amd64)  PLAT="linux-amd64" ;;
  *) echo "❌ 未知架构: $ARCH"; exit 1 ;;
esac

# 找二进制（优先当前平台目录，再回退到根目录）
VERSION=$(cat deploy/version.txt 2>/dev/null || echo "0.0.0")
GW_BIN=""
for candidate in \
  "deploy/${VERSION}/${PLAT}/computehub" \
  "deploy/${PLAT}/computehub" \
  "deploy/computehub"; do
  if [ -f "$candidate" ]; then
    GW_BIN="$candidate"
    break
  fi
done

if [ -z "$GW_BIN" ]; then
  echo "❌ 找不到 computehub 二进制"
  echo "   先编译: bash scripts/build_all.sh 或 bash scripts/build-deploy.sh"
  exit 1
fi

echo "🔍 版本: v${VERSION}, 架构: ${PLAT}"
echo "📦 二进制: ${GW_BIN}"

CMD="${1:-start}"
case "$CMD" in
  stop)
    echo "🛑 停止 Gateway..."
    pkill -f "computehub gateway" 2>/dev/null || true
    fuser -k 8282/tcp 2>/dev/null || true
    sleep 1
    echo "✅ 已停止"
    exit 0
    ;;
  restart)
    echo "🔄 重启 Gateway..."
    pkill -f "computehub gateway" 2>/dev/null || true
    fuser -k 8282/tcp 2>/dev/null || true
    sleep 1
    ;;
  status)
    if pgrep -f "computehub gateway" > /dev/null 2>&1; then
      GW_PID=$(pgrep -f "computehub gateway" | head -1)
      echo "✅ Gateway 运行中 (PID: ${GW_PID})"
      curl -s --connect-timeout 3 "http://localhost:8282/api/health" 2>/dev/null \
        && echo "📍 http://localhost:8282/health: OK" \
        || echo "⚠️  http://localhost:8282 未响应"
    else
      echo "❌ Gateway 未运行"
    fi
    exit 0
    ;;
  start)
    if pgrep -f "computehub gateway" > /dev/null 2>&1; then
      echo "✅ Gateway 已在运行 (PID: $(pgrep -f 'computehub gateway' | head -1))"
      echo "   重启: $0 restart"
      exit 0
    fi
    ;;
esac

# 启动
echo "🚀 启动 Gateway..."
echo "   工作目录: ${PROJECT_DIR}"
echo "   命令: ${GW_BIN} gateway --port 8282"
(
  cd "$PROJECT_DIR"
  nohup "$GW_BIN" gateway --port 8282 > /tmp/computehub-gateway.log 2>&1 &
  echo $! > /tmp/computehub-gateway.pid
) &
GW_PID=$!
echo "   PID: ${GW_PID}"

# 等待就绪
for i in $(seq 1 10); do
  sleep 1
  if curl -s "http://localhost:8282/api/health" > /dev/null 2>&1; then
    echo "✅ Gateway 启动成功 (${i}s)"
    echo "   📍 http://localhost:8282"
    echo "   📋 /tmp/computehub-gateway.log"
    exit 0
  fi
done

echo "❌ Gateway 启动超时，请检查日志: /tmp/computehub-gateway.log"
exit 1
