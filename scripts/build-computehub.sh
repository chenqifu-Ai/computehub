#!/bin/bash
# ==============================================================
# ComputeHub 一键构建部署脚本
# 规范 MCP-BUILD-001: 始终 CGO_ENABLED=0 编译
# 用法:
#   ./scripts/build-computehub.sh             # 构建所有
#   ./scripts/build-computehub.sh gateway     # 只构建 gateway
#   ./scripts/build-computehub.sh tui         # 只构建 tui
#   ./scripts/build-computehub.sh worker      # 只构建 worker
#   ./scripts/build-computehub.sh all restart # 构建 + 重启服务
# ==============================================================
set -e

PROJECT_DIR="/root/.openclaw/workspace/projects/computehub"
BIN_DIR="$PROJECT_DIR/code/bin"
BUILD_DIR="/tmp/computehub-build"

COMPONENTS=()
if [ $# -eq 0 ] || [[ "$1" == "all" ]]; then
  COMPONENTS=("gateway" "tui" "worker")
else
  COMPONENTS=("$1")
fi

RESTART=false
if [[ "$2" == "restart" ]] || [[ "$1" == "restart" ]]; then
  RESTART=true
fi

mkdir -p "$BIN_DIR" "$BUILD_DIR"
cd "$PROJECT_DIR"

echo "🔨 ComputeHub 构建部署 (CGO_ENABLED=0)"
echo "================================================"

for COMPONENT in "${COMPONENTS[@]}"; do
  echo ""
  echo "▶ 构建 $COMPONENT ..."
  
  case "$COMPONENT" in
    gateway) SRC="cmd/gateway/main.go"; OUT="computehub-gateway" ;;
    tui)     SRC="cmd/tui/main.go";     OUT="computehub-tui" ;;
    worker)  SRC="cmd/worker/main.go";  OUT="computehub-worker" ;;
    *)
      echo "❌ 未知组件: $COMPONENT (可选: gateway/tui/worker)"
      exit 1
      ;;
  esac
  
  CGO_ENABLED=0 go build -o "$BUILD_DIR/$OUT" "$SRC" 2>&1
  cp "$BUILD_DIR/$OUT" "$BIN_DIR/$OUT"
  
  # 显示版本
  VER=$(strings "$BIN_DIR/$OUT" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | head -1)
  SIZE=$(du -h "$BIN_DIR/$OUT" | cut -f1)
  echo "  ✅ $OUT v$VER ($SIZE)"
done

echo ""
echo "================================================"
echo "🎉 构建完成！二进制位于: $BIN_DIR/"

if $RESTART; then
  echo ""
  echo "🔄 重启服务..."
  
  # 停止旧进程
  for PROC in computehub-gateway computehub-tui; do
    PID=$(pgrep -f "$PROC" | head -1)
    if [ -n "$PID" ]; then
      kill "$PID" 2>/dev/null
      echo "  ⏹ 已停止 $PROC (PID: $PID)"
      sleep 1
    fi
  done
  
  # 启动 gateway
  nohup "$BIN_DIR/computehub-gateway" > /tmp/computehub-gateway.log 2>&1 &
  echo "  ✅ Gateway 启动 (PID: $!)"
  sleep 2
  
  # 启动 tui
  nohup "$BIN_DIR/computehub-tui" > /tmp/computehub-tui.log 2>&1 &
  echo "  ✅ TUI 启动 (PID: $!)"
  
  echo ""
  echo "🔍 验证..."
  sleep 1
  for PROC in computehub-gateway computehub-tui; do
    PID=$(pgrep -f "$PROC" | head -1)
    if [ -n "$PID" ]; then
      echo "  ✅ $PROC 运行中 (PID: $PID)"
    else
      echo "  ❌ $PROC 未运行"
    fi
  done
fi
