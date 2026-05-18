#!/bin/bash
# ============================================================
# gallery-upload.sh — 上传 ComputeHub 三合一二进制到 Gallery
# 对齐 STD-CONFIG-001 v1.1
#
# 工作流程:
#   build 产物 (bin/{platform}/computehub)
#     → sync 到 deploy/ (deploy.sh sync)
#       → find 最新三合一二进制
#         → POST 到 Gateway /api/v1/gallery/upload
#           → Worker 可通过 upgrade.sh 零SSH下载升级
#
# 用法:
#   bash scripts/gallery-upload.sh                          # 默认: http://localhost:8282
#   bash scripts/gallery-upload.sh <GATEWAY_URL>             # 指定 Gateway
#   bash scripts/gallery-upload.sh <GATEWAY_URL> <PLATFORM>  # 指定平台
#
# 示例:
#   bash scripts/gallery-upload.sh http://36.250.122.43:8282
#   bash scripts/gallery-upload.sh http://36.250.122.43:8282 linux-arm64
#   bash scripts/gallery-upload.sh http://36.250.122.43:8282 linux-arm64 linux-amd64
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
DEPLOY_DIR="${PROJECT_DIR}/deploy"
BIN_DIR="${PROJECT_DIR}/bin"

GW="${1:-http://localhost:8282}"
shift 2>/dev/null || true

# ── 检测当前平台 ──────────────────────────────────────────

detect_platform() {
  local arch=$(uname -m)
  case "$arch" in
    aarch64|arm64) echo "linux-arm64" ;;
    x86_64|amd64)  echo "linux-amd64" ;;
    *)             echo "" ;;
  esac
}

CURRENT_PLATFORM=$(detect_platform)

# ── 确定要上传的平台 ──────────────────────────────────────
# 默认: 当前平台 + linux-arm64 + linux-amd64
# 去重: 用关联数组

declare -A PLATFORM_SET
if [ $# -ge 1 ]; then
  for p in "$@"; do PLATFORM_SET["$p"]=1; done
else
  PLATFORM_SET["$CURRENT_PLATFORM"]=1
  PLATFORM_SET["linux-arm64"]=1
  PLATFORM_SET["linux-amd64"]=1
fi
PLATFORMS=("${!PLATFORM_SET[@]}")

# ── 工具函数 ──────────────────────────────────────────────

get_version() {
  cat "${DEPLOY_DIR}/version.txt" 2>/dev/null || \
    grep 'VERSION = "' src/version/version.go | awk -F'"' '{print $2}'
}

find_binary() {
  # find_binary <platform> → 只找三合一二进制 computehub（不含 -gateway/-worker/-tui）
  # 优先级: bin/ → deploy/{version}/ → deploy/{platform}/ → deploy/ 根目录
  local platform="$1"
  local ext=""; [[ "$platform" == windows-* ]] && ext=".exe"
  local version=$(get_version)

  for dir in \
    "${BIN_DIR}" \
    "${DEPLOY_DIR}/${version}" \
    "${DEPLOY_DIR}"; do
    local f="${dir}/${platform}/computehub${ext}"
    if [ -f "$f" ] && [ ! -L "$f" ]; then
      # 确认是三合一（不是旧版单入口）
      local size
      size=$(stat -c%s "$f" 2>/dev/null || echo "0")
      # 三合一二进制应该 ≥ 5MB
      [ "$size" -ge 5000000 ] && { echo "$f"; return 0; }
    fi
  done

  # 最后查根目录
  local root="${DEPLOY_DIR}/computehub${ext}"
  if [ -f "$root" ]; then
    local size=$(stat -c%s "$root" 2>/dev/null || echo "0")
    [ "$size" -ge 5000000 ] && { echo "$root"; return 0; }
  fi

  return 1
}

# ── 如果没编译，自动 build ────────────────────────────────

ensure_binaries() {
  local need_build=false
  for plat in "${PLATFORMS[@]}"; do
    if ! find_binary "$plat" >/dev/null 2>&1; then
      need_build=true
      break
    fi
  done

  if $need_build; then
    echo "  🔨 未找到 ${PLATFORMS[*]} 的编译产物，自动编译..."
    bash "$(dirname "$0")/deploy.sh" build
    # build 之后自动 sync，deploy/ 下就有新产物了
  fi
}

# ── 上传单个文件 ──────────────────────────────────────────

upload_one() {
  local platform="$1"
  local src="$2"
  local size=$(stat -c%s "$src" 2>/dev/null || echo "0")
  local mb=$(awk "BEGIN{printf \"%.1f\", $size/1024/1024}")

  # 上传后的文件名: computehub-linux-arm64, computehub-linux-amd64
  local upload_name="computehub-${platform}"
  local version=$(get_version)

  echo ""
  echo "  📦 ${upload_name} (${mb} MB, v${version})"
  echo "     源文件: ${src}"

  # 上传时指定文件名，方便 Worker 通过固定 URL 下载
  RESP=$(curl -s --connect-timeout 10 \
    -F "file=@${src};filename=${upload_name}" \
    "${GW}/api/v1/gallery/upload" 2>/dev/null)

  if echo "$RESP" | grep -q '"success":true'; then
    local fname
    fname=$(echo "$RESP" | python3 -c "
import json,sys
try:
    print(json.load(sys.stdin)['data']['name'])
except: pass
" 2>/dev/null)
    echo "     ✅ 已上传 → ${GW}/api/v1/files/${fname}"
    echo "     📥 Worker 下载: wget -O computehub ${GW}/api/v1/files/${upload_name}"
    return 0
  else
    local err_msg=$(echo "$RESP" | head -c 120)
    echo "     ❌ 上传失败: ${err_msg}"
    return 1
  fi
}

# ── Main ──────────────────────────────────────────────────

echo "📤 Gallery 二进制上传"
echo "   Gateway: ${GW}"
echo "   平台:    ${PLATFORMS[*]}"
echo "=============================="

# 1. 检查 Gateway
HEALTH=$(curl -s --connect-timeout 5 "${GW}/api/health" 2>/dev/null)
if ! echo "$HEALTH" | grep -qi "healthy\|success"; then
  echo " ❌ Gateway 不可达: ${GW}"
  exit 1
fi
echo " ✅ Gateway 正常"

# 2. 确保有二进制
ensure_binaries

# 3. 上传
echo ""
echo "⬆️  开始上传..."
UPLOADED=0
FAILED=0

for plat in "${PLATFORMS[@]}"; do
  src=$(find_binary "$plat") || {
    echo ""
    echo "  ⚠️  ${plat}: 无三合一二进制（至少 5MB），跳过"
    FAILED=$((FAILED + 1))
    continue
  }
  if upload_one "$plat" "$src"; then
    UPLOADED=$((UPLOADED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "=============================="
echo "✅ 完成! ${UPLOADED} 上传成功, ${FAILED} 失败"
echo ""
echo "💡 后续操作:"
echo "   # 远程升级所有 Worker（零 SSH）"
echo "   bash scripts/upgrade.sh ${GW}"
echo ""
echo "   # 或在 Worker 节点手动下载:"
echo "   wget -O /usr/local/bin/computehub ${GW}/api/v1/files/computehub-linux-arm64"
echo "   chmod +x /usr/local/bin/computehub"
