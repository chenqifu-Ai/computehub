#!/bin/bash
# ============================================================
# control.sh — ComputeHub 统一启停管理
# 对齐 STD-CONFIG-001 v1.1
#
# 用法:
#   control.sh status                       # 全部状态
#   control.sh start gateway                # 启动 Gateway
#   control.sh start worker --gw <url>      # 启动 Worker
#   control.sh start tui --gw <url>         # 启动 TUI
#   control.sh stop gateway                 # 停止 Gateway
#   control.sh stop all                     # 停止全部
#   control.sh restart gateway              # 重启 Gateway
#   control.sh logs gateway                 # 查看日志
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
DEPLOY_DIR="${PROJECT_DIR}/deploy"
VERSION=$(cat "${DEPLOY_DIR}/version.txt" 2>/dev/null || echo "0.0.0")
LOG_DIR="/tmp/computehub"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()  { echo -e "  ${GREEN}${1}${NC}"; }
warn(){ echo -e "  ${YELLOW}${1}${NC}"; }
err() { echo -e "  ${RED}${1}${NC}"; }

# ── 找二进制 ──────────────────────────────────────────────

find_binary() {
  local arch=$(uname -m)
  case "$arch" in
    aarch64|arm64) local plat="linux-arm64" ;;
    x86_64|amd64)  local plat="linux-amd64" ;;
    *) err "未知架构: $arch"; exit 1 ;;
  esac

  for f in \
    "${DEPLOY_DIR}/${VERSION}/${plat}/computehub" \
    "${DEPLOY_DIR}/${plat}/computehub" \
    "${DEPLOY_DIR}/computehub"; do
    [ -f "$f" ] && { echo "$f"; return; }
  done

  err "找不到 computehub 二进制 (${plat})，先 build"; exit 1
}

BINARY=$(find_binary)

# ── 确保日志目录 ──────────────────────────────────────────

ensure_log_dir() {
  mkdir -p "$LOG_DIR"
}

# ── Gateway ──────────────────────────────────────────────

gateway_start() {
  ensure_log_dir
  if pgrep -f "computehub gateway" >/dev/null 2>&1; then
    warn "Gateway 已在运行 (PID: $(pgrep -f 'computehub gateway' | head -1))"
    return 0
  fi

  echo "🚀 启动 Gateway..."
  cd "$PROJECT_DIR"
  nohup "$BINARY" gateway --port "${PORT:-8282}" > "${LOG_DIR}/gateway.log" 2>&1 &
  local pid=$!
  echo "   PID: ${pid}"

  for i in $(seq 1 10); do
    sleep 1
    if curl -s "http://localhost:${PORT:-8282}/api/health" >/dev/null 2>&1; then
      ok "Gateway 启动成功 (${i}s) — http://localhost:${PORT:-8282}"
      return 0
    fi
  done

  err "Gateway 启动超时"
  warn "日志: ${LOG_DIR}/gateway.log"
  return 1
}

gateway_stop() {
  echo "🛑 停止 Gateway..."
  pkill -f "computehub gateway" 2>/dev/null || true
  fuser -k "${PORT:-8282}/tcp" 2>/dev/null || true
  sleep 1
  ok "Gateway 已停止"
}

gateway_status() {
  if pgrep -f "computehub gateway" >/dev/null 2>&1; then
    local pid=$(pgrep -f "computehub gateway" | head -1)
    local health="未响应"
    curl -s --connect-timeout 3 "http://localhost:${PORT:-8282}/api/health" >/dev/null 2>&1 && health="正常"
    echo "  Gateway: ✅ 运行中 (PID: ${pid}) — ${health}"
  else
    echo "  Gateway: ❌ 未运行"
  fi
}

gateway_logs() {
  tail -f "${LOG_DIR}/gateway.log"
}

# ── Worker ────────────────────────────────────────────────

worker_start() {
  ensure_log_dir
  local gw="${GW_URL:-http://localhost:8282}"
  local node_id="${NODE_ID:-$(hostname)-worker}"
  local concurrent="${CONCURRENT:-4}"
  local interval="${INTERVAL:-3}"

  if pgrep -f "computehub worker" >/dev/null 2>&1; then
    warn "Worker 已在运行 (PID: $(pgrep -f 'computehub worker' | head -1))"
    return 0
  fi

  echo "🚀 启动 Worker..."
  echo "   Gateway: ${gw}"
  echo "   Node ID: ${node_id}"
  echo "   并发数: ${concurrent}"

  nohup "$BINARY" worker \
    --gw "${gw}" \
    --node-id "${node_id}" \
    --interval "${interval}" \
    --concurrent "${concurrent}" \
    > "${LOG_DIR}/worker.log" 2>&1 &
  local pid=$!
  sleep 2

  if kill -0 "$pid" 2>/dev/null; then
    ok "Worker 启动成功 (PID: ${pid})"
  else
    err "Worker 启动失败"
    warn "日志: ${LOG_DIR}/worker.log"
    return 1
  fi
}

worker_stop() {
  echo "🛑 停止 Worker..."
  pkill -f "computehub worker" 2>/dev/null || true
  sleep 1
  ok "Worker 已停止"
}

worker_status() {
  if pgrep -f "computehub worker" >/dev/null 2>&1; then
    local pid=$(pgrep -f "computehub worker" | head -1)
    echo "  Worker: ✅ 运行中 (PID: ${pid})"
  else
    echo "  Worker: ❌ 未运行"
  fi
}

worker_logs() {
  tail -f "${LOG_DIR}/worker.log"
}

# ── TUI ──────────────────────────────────────────────────

tui_start() {
  local gw="${GW_URL:-localhost:8282}"

  if pgrep -f "computehub tui" >/dev/null 2>&1; then
    warn "TUI 已在运行"
    return 0
  fi

  echo "🚀 启动 TUI (网关: ${gw})..."
  "$BINARY" tui --gw "$gw"
}

tui_stop() {
  echo "🛑 停止 TUI..."
  pkill -f "computehub tui" 2>/dev/null || true
  ok "TUI 已停止"
}

tui_status() {
  if pgrep -f "computehub tui" >/dev/null 2>&1; then
    local pid=$(pgrep -f "computehub tui" | head -1)
    echo "  TUI:    ✅ 运行中 (PID: ${pid})"
  else
    echo "  TUI:    ❌ 未运行"
  fi
}

# ── Main ──────────────────────────────────────────────────

usage() {
  echo "ComputeHub 启停管理 (STD-CONFIG-001)"
  echo ""
  echo "用法:"
  echo "  bash scripts/control.sh status                       # 全部状态"
  echo "  bash scripts/control.sh start gateway [--port N]     # 启动 Gateway"
  echo "  bash scripts/control.sh start worker [--gw URL] ...  # 启动 Worker"
  echo "  bash scripts/control.sh start tui [--gw HOST:PORT]   # 启动 TUI"
  echo "  bash scripts/control.sh stop gateway|worker|tui|all  # 停止"
  echo "  bash scripts/control.sh restart gateway|worker       # 重启"
  echo "  bash scripts/control.sh logs gateway|worker          # 实时日志"
  echo ""
  echo "Worker 参数:"
  echo "  --gw <url>           Gateway 地址 (默认: http://localhost:8282)"
  echo "  --node-id <id>       节点 ID (默认: hostname-worker)"
  echo "  --concurrent <N>     并发数 (默认: 4)"
  echo "  --interval <N>       轮询间隔秒 (默认: 3)"
  echo ""
  echo "示例:"
  echo "  bash scripts/control.sh start gateway --port 8282"
  echo "  bash scripts/control.sh start worker --gw http://36.250.122.43:8282 --concurrent 8"
  echo "  bash scripts/control.sh restart gateway"
  echo "  bash scripts/control.sh logs worker"
}

CMD="${1:-help}"; [ $# -gt 0 ] && shift
ACTION="$CMD"

SUB_CMD="${1:-}"; [ $# -gt 0 ] && shift

# 解析通用参数（在 subcommand 之后）
PORT="8282"
GW_URL=""
NODE_ID=""
CONCURRENT="4"
INTERVAL="3"

while [ $# -gt 0 ]; do
  case "$1" in
    --port)      shift; PORT="$1" ;;
    --gw)        shift; GW_URL="$1" ;;
    --node-id)   shift; NODE_ID="$1" ;;
    --concurrent) shift; CONCURRENT="$1" ;;
    --interval)  shift; INTERVAL="$1" ;;
    *)           shift ;;
  esac
  shift 2>/dev/null || true
done

case "$ACTION" in
  start)
    case "$SUB_CMD" in
      gateway)  gateway_start ;;
      worker)   worker_start ;;
      tui)      tui_start ;;
      *)        err "start 需要目标: gateway | worker | tui"; usage; exit 1 ;;
    esac
    ;;
  stop)
    case "$SUB_CMD" in
      gateway)  gateway_stop ;;
      worker)   worker_stop ;;
      tui)      tui_stop ;;
      all)      gateway_stop; worker_stop; tui_stop ;;
      *)        err "stop 需要目标: gateway | worker | tui | all"; usage; exit 1 ;;
    esac
    ;;
  restart)
    case "$SUB_CMD" in
      gateway)  gateway_stop; gateway_start ;;
      worker)   worker_stop; worker_start ;;
      *)        err "restart 需要目标: gateway | worker"; usage; exit 1 ;;
    esac
    ;;
  status)
    echo "📊 ComputeHub 状态 (v${VERSION})"
    echo "   二进制: ${BINARY}"
    gateway_status
    worker_status
    tui_status
    ;;
  logs)
    case "$SUB_CMD" in
      gateway)  gateway_logs ;;
      worker)   worker_logs ;;
      *)        err "logs 需要目标: gateway | worker"; usage; exit 1 ;;
    esac
    ;;
  help|--help|-h) usage ;;
  *)  err "未知命令: $ACTION"; usage; exit 1 ;;
esac
