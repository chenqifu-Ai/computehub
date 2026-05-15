#!/bin/bash
# sync-deploy.sh — 将编译好的 binary 同步组织到 deploy/ 目录
# 用法:
#   bash scripts/sync-deploy.sh                    # 本地同步（从 bin/ 或 deploy/ 整理）
#   bash scripts/sync-deploy.sh push <host> <password> [user]
#   bash scripts/sync-deploy.sh push 192.168.2.140 '密码' chenqifu

set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
BIN_DIR="${PROJECT_DIR}/bin"
DEPLOY_DIR="${PROJECT_DIR}/deploy"
VERSION=$(grep 'VERSION = "' src/version/version.go | awk -F'"' '{print $2}')

echo "🔁 Sync deploy (v${VERSION})"
echo "===================================="

# ---- 找二进制：优先 bin/，回退 deploy/{platform}/
find_binary() {
  local platform="$1"
  local os="${platform%%-*}"
  local ext=""; [ "$os" = "windows" ] && ext=".exe"

  # 尝试顺序: bin/ → deploy/{version} → deploy/
  for dir in "${BIN_DIR}" "${DEPLOY_DIR}/${VERSION}" "${DEPLOY_DIR}"; do
    local f="${dir}/${platform}/computehub${ext}"
    if [ -f "$f" ]; then
      echo "$f"
      return 0
    fi
  done

  # 也看看 deploy/ 根目录
  local root_f="${DEPLOY_DIR}/computehub${ext}"
  [ -f "$root_f" ] && echo "$root_f" && return 0

  return 1
}

PLATFORMS=("linux-amd64" "linux-arm64" "darwin-amd64" "darwin-arm64" "windows-amd64")

# 1. 同步到 deploy/{version}/{platform}/
echo ""
echo "📂 Step 1: deploy/${VERSION}/{platform}/"
for plat in "${PLATFORMS[@]}"; do
  src=$(find_binary "$plat") || true
  dst_dir="${DEPLOY_DIR}/${VERSION}/${plat}"
  mkdir -p "$dst_dir"
  os="${plat%%-*}"
  ext=""; [ "$os" = "windows" ] && ext=".exe"

  if [ -n "$src" ]; then
    cp "$src" "${dst_dir}/computehub${ext}"
    chmod +x "${dst_dir}/computehub${ext}" 2>/dev/null || true
    echo "  ✅ ${plat} ← $(basename $(dirname $src))"
  else
    echo "  ⚠️  ${plat}: 无二进制"
  fi
done

# 2. 同步到 deploy/{platform}/（平铺）
echo ""
echo "📂 Step 2: deploy/{platform}/"
for plat in "${PLATFORMS[@]}"; do
  src=$(find_binary "$plat") || true
  dst_dir="${DEPLOY_DIR}/${plat}"
  mkdir -p "$dst_dir"
  os="${plat%%-*}"
  ext=""; [ "$os" = "windows" ] && ext=".exe"

  if [ -n "$src" ]; then
    cp "$src" "${dst_dir}/computehub${ext}"
    chmod +x "${dst_dir}/computehub${ext}" 2>/dev/null || true
    echo "  ✅ ${plat}/computehub${ext}"
  fi
done

# 3. 当前平台到 deploy/ 根目录
echo ""
echo "📂 Step 3: deploy/computehub (当前平台)"
CUR_PLAT="linux-arm64"
case "$(uname -s),$(uname -m)" in
  Linux,aarch64|Linux,arm64)  CUR_PLAT="linux-arm64" ;;
  Linux,x86_64|Linux,amd64)   CUR_PLAT="linux-amd64" ;;
  Darwin,arm64|Darwin,aarch64) CUR_PLAT="darwin-arm64" ;;
  Darwin,x86_64|Darwin,amd64)  CUR_PLAT="darwin-amd64" ;;
esac

src=$(find_binary "$CUR_PLAT") || true
if [ -n "$src" ]; then
  os="${CUR_PLAT%%-*}"
  ext=""; [ "$os" = "windows" ] && ext=".exe"
  cp "$src" "${DEPLOY_DIR}/computehub${ext}"
  chmod +x "${DEPLOY_DIR}/computehub${ext}" 2>/dev/null || true
  echo "  ✅ deploy/computehub${ext} (${CUR_PLAT})"
else
  echo "  ⚠️  当前平台 ${CUR_PLAT} 无二进制"
fi

# 4. sha256sums
echo ""
echo "📝 Step 4: sha256sums"
cd "${DEPLOY_DIR}"
find . -type f \( -name "computehub" -o -name "computehub.exe" \) | sort | xargs sha256sum > "sha256sums-${VERSION}.txt" 2>/dev/null || echo "  ⚠️  sha256sum 生成失败（可能无二进制）"
echo "  ✅ deploy/sha256sums-${VERSION}.txt"

echo ""
echo "✅ 同步完成!"

# ==========================================================
# 远程推送
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

  REMOTE_ARCH="linux-amd64"
  if command -v sshpass > /dev/null 2>&1; then
    REMOTE_ARCH=$(sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "uname -m" 2>/dev/null | tr -d '\r')
    case "$REMOTE_ARCH" in
      aarch64|arm64) REMOTE_ARCH="linux-arm64" ;;
      x86_64|amd64)  REMOTE_ARCH="linux-amd64" ;;
      *)             echo "  ⚠️  未知架构: $REMOTE_ARCH，默认 linux-amd64" ;;
    esac
  fi

  src=$(find_binary "$REMOTE_ARCH") || true
  if [ -z "$src" ]; then
    echo "  ❌ 无 ${REMOTE_ARCH} 二进制"
    exit 1
  fi

  echo "  📄 $(basename $src) → ${REMOTE_USER}@${REMOTE_HOST}:~/computehub"
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
