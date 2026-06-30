#!/bin/bash
# start-tui.sh — 启动 ComputeHub TUI（三合一版本）
# 用法: start-tui.sh              （启动，默认本地 8282）
#        start-tui.sh --gw <URL>  （指定网关地址）
#        start-tui.sh stop
#        start-tui.sh status

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BINARY="${PROJECT_DIR}/deploy/computehub"
LOG_FILE="/tmp/computehub-tui.log"
PID_FILE="/tmp/computehub-tui.pid"

log()   { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }
error() { echo "[ERROR] $1" >&2; exit 1; }

# 找二进制
if [ ! -f "$BINARY" ]; then
  # 按架构找
  ARCH=$(uname -m)
  case "$ARCH" in
    aarch64|arm64) PLAT="linux-arm64" ;;
    x86_64|amd64)  PLAT="linux-amd64" ;;
  esac
  VERSION=$(cat "${PROJECT_DIR}/deploy/version.txt" 2>/dev/null || echo "0.0.0")
  for c in \
    "${PROJECT_DIR}/deploy/${VERSION}/${PLAT}/computehub" \
    "${PROJECT_DIR}/deploy/${PLAT}/computehub"; do
    [ -f "$c" ] && { BINARY="$c"; break; }
  done
fi

[ ! -f "$BINARY" ] && error "找不到 computehub 二进制，先运行 build_all.sh 或 build-deploy.sh"
[ ! -x "$BINARY" ] && chmod +x "$BINARY"

GW_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --gw) shift; GW_ARG="--gw $1" ;;
    *)    break ;;
  esac
  shift
done

CMD="${1:-start}"
case "$CMD" in
  stop)
    log "停止 TUI..."
    if [ -f "$PID_FILE" ]; then
      pid=$(cat "$PID_FILE")
      kill "$pid" 2>/dev/null || true
      rm -f "$PID_FILE"
    fi
    pkill -f "computehub tui" 2>/dev/null || true
    log "已停止"
    exit 0
    ;;
  status)
    if [ -f "$PID_FILE" ]; then
      pid=$(cat "$PID_FILE")
      if kill -0 "$pid" 2>/dev/null; then
        log "TUI 运行中 (PID: $pid)"
        exit 0
      fi
      rm -f "$PID_FILE"
    fi
    if pgrep -f "computehub tui" > /dev/null 2>&1; then
      log "TUI 运行中 (PID: $(pgrep -f 'computehub tui' | head -1))"
    else
      log "TUI 未运行"
    fi
    exit 0
    ;;
  start)
    if [ -f "$PID_FILE" ]; then
      pid=$(cat "$PID_FILE")
      if kill -0 "$pid" 2>/dev/null; then
        log "TUI 已在运行 (PID: $pid)"
        exit 0
      fi
      rm -f "$PID_FILE"
    fi
    ;;
esac

log "启动 ComputeHub TUI..."
log "二进制: $BINARY"
log "网关:   ${GW_ARG:--}"  # will show "-" if not set
log "日志:   $LOG_FILE"

nohup "$BINARY" tui $GW_ARG > "$LOG_FILE" 2>&1 &
pid=$!
echo "$pid" > "$PID_FILE"
sleep 2

if kill -0 "$pid" 2>/dev/null; then
  log "TUI 启动成功 (PID: $pid)"
  log "查看日志: tail -f $LOG_FILE"
else
  error "TUI 启动失败，日志: $LOG_FILE"
fi
