#!/bin/bash
# sync-deploy.sh — 将 bin/ 新编译的二进制同步到 deploy/ 目录
# 用法:
#   bash scripts/sync-deploy.sh                    # 仅本地同步
#   bash scripts/sync-deploy.sh push <host> <password> [user]
#   bash scripts/sync-deploy.sh push 192.168.2.140 '密码' chenqifu

set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
BIN_DIR="${PROJECT_DIR}/bin"
DEPLOY_DIR="${PROJECT_DIR}/deploy"
VERSION=$(cat "${DEPLOY_DIR}/version.txt" 2>/dev/null || echo "0.0.0")

echo "🔁 Sync bin/ → deploy/ (v${VERSION})"
echo "===================================="

# 1. 同步到 deploy/{version}/{platform}/
echo ""
echo "📂 Step 1: deploy/${VERSION}/{platform}/"
for plat in linux-amd64 linux-arm64 darwin-amd64 darwin-arm64 windows-amd64; do
  src_dir="${BIN_DIR}/${plat}"
  dst_dir="${DEPLOY_DIR}/${VERSION}/${plat}"
  if [ ! -d "$src_dir" ]; then
    echo "  ⚠️  ${plat}: bin/ 无此目录，跳过"
    continue
  fi
  mkdir -p "$dst_dir"
  count=0
  for f in "${src_dir}"/computehub-*; do
    [ -f "$f" ] || continue
    cp "$f" "$dst_dir/"
    count=$((count + 1))
  done
  echo "  ✅ ${plat}: ${count} 个文件"
done

# 2. 同步到 deploy/ 根目录（扁平命名: computehub-{comp}-{platform}）
echo ""
echo "📂 Step 2: deploy/ (扁平命名)"
count=0
for plat in linux-amd64 linux-arm64 darwin-amd64 darwin-arm64 windows-amd64; do
  src_dir="${BIN_DIR}/${plat}"
  [ -d "$src_dir" ] || continue
  for f in "${src_dir}"/computehub-*; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    base="${name%.exe}"
    ext=""
    [[ "$name" == *.exe ]] && ext=".exe"
    flat_name="${base}-${plat}${ext}"
    cp "$f" "${DEPLOY_DIR}/${flat_name}"
    count=$((count + 1))
  done
done
echo "  ✅ ${count} 个文件"

# 3. 重新生成 sha256sums
echo ""
echo "📝 Step 3: sha256sums"
cd "${DEPLOY_DIR}/${VERSION}"
find . -type f -name "computehub-*" | sort | xargs sha256sum > sha256sums.txt
echo "  ✅ deploy/${VERSION}/sha256sums.txt"

cd "${DEPLOY_DIR}"
find . -maxdepth 1 -type f -name "computehub-*" | sort | xargs sha256sum > sha256sums-${VERSION}.txt
echo "  ✅ deploy/sha256sums-${VERSION}.txt"

echo ""
echo "✅ 同步完成!"

echo ""
echo "✅ 全部完成！文件位置："
echo "   deploy/${VERSION}/{platform}/computehub-{gateway,worker,tui}"
echo "   deploy/computehub-{gateway,worker,tui}-{platform}"

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
      echo "用法: $0 [push <host> <password> [user]]"
      exit 1
      ;;
  esac
fi
  echo ""
  echo "📤 Step 4: 远程推送 → ${REMOTE_USER}@${REMOTE_HOST}"

  # 确定远程架构（默认 linux-amd64）
  REMOTE_ARCH="linux-amd64"
  if command -v sshpass > /dev/null 2>&1; then
    REMOTE_ARCH=$(sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "uname -m" 2>/dev/null | tr -d '\r')
    case "$REMOTE_ARCH" in
      aarch64|arm64) REMOTE_ARCH="linux-arm64" ;;
      x86_64|amd64)  REMOTE_ARCH="linux-amd64" ;;
      *)             echo "  ⚠️  未知架构: $REMOTE_ARCH，默认 linux-amd64" ;;
    esac
  fi

  # 推送三个二进制
  for comp in gateway worker tui; do
    src="${DEPLOY_DIR}/computehub-${comp}-${REMOTE_ARCH}"
    if [ ! -f "$src" ]; then
      echo "  ⚠️  ${src} 不存在，跳过"
      continue
    fi
    echo "  📄 computehub-${comp} → ${REMOTE_USER}@${REMOTE_HOST}:~/"
    sshpass -p "$REMOTE_PASS" scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$src" "${REMOTE_USER}@${REMOTE_HOST}:~/computehub-${comp}" 2>/dev/null
    sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "chmod +x ~/computehub-${comp}" 2>/dev/null
    echo "     ✅"
  done

  echo "  ✅ 远程推送完成"
  echo "  远程文件: ~/computehub-{gateway,worker,tui}"
  echo "  远程安装: sudo cp ~/computehub-* /usr/local/bin/"
fi

echo ""
echo "💡 提示：若需验证 download 端点，请确认 Gateway 运行中"
echo "   bash scripts/start-gateway.sh"
echo "   然后: curl http://localhost:8282/api/v1/download?file=computehub-worker-linux-amd64 -o /dev/null -w '%{http_code}'"
