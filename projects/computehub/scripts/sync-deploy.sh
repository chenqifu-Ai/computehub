#!/bin/bash
# sync-deploy.sh — 将 bin/ 新编译的单一二进制同步到 deploy/ 目录
# 用法:
#   bash scripts/sync-deploy.sh                    # 仅本地同步
#   bash scripts/sync-deploy.sh push <host> <password> [user]
#   bash scripts/sync-deploy.sh push 192.168.2.140 '密码' chenqifu

set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
BIN_DIR="${PROJECT_DIR}/bin"
DEPLOY_DIR="${PROJECT_DIR}/deploy"
VERSION=$(grep 'var VERSION' src/version/version.go | awk -F'"' '{print $2}')

echo "🔁 Sync bin/ → deploy/ (v${VERSION})"
echo "===================================="

# 1. 同步到 deploy/{version}/{platform}/
echo ""
echo "📂 Step 1: deploy/${VERSION}/{platform}/computehub"
for plat in linux-amd64 linux-arm64 darwin-amd64 darwin-arm64 windows-amd64; do
  src="${BIN_DIR}/${plat}/computehub"
  src_exe="${BIN_DIR}/${plat}/computehub.exe"
  dst_dir="${DEPLOY_DIR}/${VERSION}/${plat}"
  mkdir -p "$dst_dir"

  if [ -f "$src" ]; then
    cp "$src" "${dst_dir}/computehub"
    echo "  ✅ ${plat}: computehub"
  elif [ -f "$src_exe" ]; then
    cp "$src_exe" "${dst_dir}/computehub.exe"
    echo "  ✅ ${plat}: computehub.exe"
  else
    echo "  ⚠️  ${plat}: 无二进制"
  fi
done

# 2. 同步到 deploy/ 根目录（当前平台 + 版本目录）
echo ""
echo "📂 Step 2: deploy/ (根目录)"
CUR_PLAT="linux-arm64"  # 默认（在 Android 上编译）
case "$(uname -s),$(uname -m)" in
  Linux,aarch64|Linux,arm64)  CUR_PLAT="linux-arm64" ;;
  Linux,x86_64|Linux,amd64)   CUR_PLAT="linux-amd64" ;;
esac

if [ -f "${BIN_DIR}/${CUR_PLAT}/computehub" ]; then
  cp "${BIN_DIR}/${CUR_PLAT}/computehub" "${DEPLOY_DIR}/computehub"
  echo "  ✅ deploy/computehub (${CUR_PLAT})"
fi

# 3. 同步各平台到 deploy/{platform}/
echo ""
echo "📂 Step 3: deploy/{platform}/computehub"
for plat in linux-amd64 linux-arm64 darwin-amd64 darwin-arm64 windows-amd64; do
  src="${BIN_DIR}/${plat}/computehub"
  src_exe="${BIN_DIR}/${plat}/computehub.exe"
  dst_dir="${DEPLOY_DIR}/${plat}"
  mkdir -p "$dst_dir"

  if [ -f "$src" ]; then
    cp "$src" "${dst_dir}/computehub"
    echo "  ✅ ${plat}/computehub"
  elif [ -f "$src_exe" ]; then
    cp "$src_exe" "${dst_dir}/computehub.exe"
    echo "  ✅ ${plat}/computehub.exe"
  fi
done

# 4. 重新生成 sha256sums
echo ""
echo "📝 Step 4: sha256sums"
cd "${DEPLOY_DIR}"
find . -type f \( -name "computehub" -o -name "computehub.exe" \) | sort | xargs sha256sum > "sha256sums-${VERSION}.txt"
echo "  ✅ deploy/sha256sums-${VERSION}.txt"

echo ""
echo "✅ 同步完成!"

# ==========================================================
# 远程推送：scp 到远程主机
# ==========================================================
REMOTE_HOST=""
REMOTE_PASS=""
REMOTE_USER="root"

if [ $# -ge 1 ]; then
  CMD="$1"; shift
  case "$CMD" in
    push)
      REMOTE_HOST="${1:-}"
      REMOTE_PASS="${2:-}"
      REMOTE_USER="${3:-root}"
      if [ -z "$REMOTE_HOST" ] || [ -z "$REMOTE_PASS" ]; then
        echo "用法: $0 push <host> <password> [user]"
        exit 1
      fi
      ;;
    *)
      echo "未知命令: $CMD"
      exit 1
      ;;
  esac
fi

if [ -n "$REMOTE_HOST" ]; then
  echo ""
  echo "📤 Step 5: 远程推送 → ${REMOTE_USER}@${REMOTE_HOST}"

  # 确定远程架构
  REMOTE_ARCH="linux-amd64"
  if command -v sshpass > /dev/null 2>&1; then
    REMOTE_ARCH=$(sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "uname -m" 2>/dev/null | tr -d '\r')
    case "$REMOTE_ARCH" in
      aarch64|arm64) REMOTE_ARCH="linux-arm64" ;;
      x86_64|amd64)  REMOTE_ARCH="linux-amd64" ;;
      *)             echo "  ⚠️  未知架构: $REMOTE_ARCH，默认 linux-amd64" ;;
    esac
  fi

  src="${BIN_DIR}/${REMOTE_ARCH}/computehub"
  [ -f "$src" ] || src="${DEPLOY_DIR}/${REMOTE_ARCH}/computehub"
  [ -f "$src" ] || { echo "  ❌ 无 ${REMOTE_ARCH} 二进制"; exit 1; }

  echo "  📄 computehub (${REMOTE_ARCH}) → ${REMOTE_USER}@${REMOTE_HOST}:~/"
  sshpass -p "$REMOTE_PASS" scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$src" "${REMOTE_USER}@${REMOTE_HOST}:~/computehub" 2>/dev/null
  sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "chmod +x ~/computehub" 2>/dev/null
  echo "  ✅ 远程推送完成"
  echo "  远程文件: ~/computehub"
  echo "  用法: ~/computehub {gateway|worker|tui} ..."
fi

echo ""
echo "💡 提示：若需验证 download 端点，请确认 Gateway 运行中"
echo "   bash scripts/start-gateway.sh"
echo "   然后: curl http://localhost:8282/api/v1/download?file=computehub&platform=linux-amd64 -o /dev/null -w '%{http_code}'"
