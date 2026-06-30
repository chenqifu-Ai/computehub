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
# 版本号统一来源
VERSION=$(bash "$(dirname "$0")/get_version.sh")
if [ -z "$VERSION" ]; then
    VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
fi

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
  cp -f "$src" "${DEPLOY_DIR}/computehub${ext}"
  chmod +x "${DEPLOY_DIR}/computehub${ext}" 2>/dev/null || true
  echo "  ✅ deploy/computehub${ext} (${CUR_PLAT})"
else
  echo "  ⚠️  当前平台 ${CUR_PLAT} 无二进制"
fi

# 4. version.txt（同步 deploy 目录时自动更新）
echo ""
echo "📝 Step 5: deploy/version.txt"
echo "${VERSION}" > "${DEPLOY_DIR}/version.txt"
echo "  ✅ deploy/version.txt → ${VERSION}"

# 5. sha256sums
echo ""
echo "📝 Step 6: sha256sums"
cd "${DEPLOY_DIR}"
find . -type f \( -name "computehub" -o -name "computehub.exe" \) | sort | xargs sha256sum > "sha256sums-${VERSION}.txt" 2>/dev/null || echo "  ⚠️  sha256sum 生成失败（可能无二进制）"
echo "  ✅ deploy/sha256sums-${VERSION}.txt"

echo ""
echo "✅ 同步完成!"

# ==========================================================
# 远程推送（精细化）
# ==========================================================
REMOTE_HOST=""
REMOTE_PASS=""
REMOTE_USER="computehub"
REMOTE_SSH_KEY="${HOME}/.ssh/id_ed25519_computehub"
REMOTE_ACTION=""   # gateway | worker | tui | none | restart-all
REMOTE_GW=""       # 远程 Gateway 地址（供 worker 连接）

if [ $# -ge 1 ]; then
  CMD="$1"; shift
  case "$CMD" in
    push)
      REMOTE_HOST="${1:-}"
      shift 2>/dev/null || true
      # 检测 $2 是否以 -- 开头 → 没有密码参数，直接走密钥
      if [ $# -gt 0 ] && [[ "${1:-}" != --* ]]; then
        REMOTE_PASS="$1"
        shift
        # 再检测 $3 是否以 -- 开头 → 没有 user 参数
        if [ $# -gt 0 ] && [[ "${1:-}" != --* ]]; then
          REMOTE_USER="$1"
          shift
        fi
      fi
      # 可指定自定义密钥
      while [ $# -gt 0 ]; do
        case "$1" in
          --key)        shift; REMOTE_SSH_KEY="$1" ;;
          --action)     shift; REMOTE_ACTION="$1" ;;
          --gateway|--gw) shift; REMOTE_GW="$1" ;;
          *) break ;;
        esac
        shift
      done
      if [ -z "$REMOTE_HOST" ]; then
        echo "用法: $0 push <host> [password] [user] [--key SSH_KEY] [--action gateway|worker|restart-all] [--gateway URL]"
        echo ""
        echo "  --key SSH_KEY    SSH 私钥路径 (默认: ~/.ssh/id_ed25519_computehub)"
        echo "  --action         推送后执行的动作 (默认: none)"
        echo "    gateway         停旧gateway→推送→装到PATH→启动gateway"
        echo "    worker          停旧worker→推送→装到PATH→启动worker"
        echo "    restart-all     停全部→推送→装→启动gateway+worker"
        echo "    none            仅推送，不执行动作"
        echo "  --gateway URL    worker 连接的 Gateway 地址 (默认: http://<host>:8282)"
        echo ""
        echo "示例:"
        echo "  bash scripts/sync-deploy.sh push 36.250.122.43 --action restart-all"
        echo "  bash scripts/sync-deploy.sh push 36.250.122.43 --action worker --gateway http://36.250.122.43:8282"
        echo "  bash scripts/sync-deploy.sh push 192.168.2.140 '密码' chenqifu --key ~/.ssh/id_rsa"
        exit 1
      fi
      # 默认动作
      [ -z "$REMOTE_ACTION" ] && REMOTE_ACTION="none"
      [ -z "$REMOTE_GW" ] && REMOTE_GW="http://${REMOTE_HOST}:8282"
      ;;
    *)
      echo "未知命令: $CMD"
      exit 1
      ;;
  esac
fi

if [ -n "$REMOTE_HOST" ]; then
  BASE_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
  # 密码优先（sshpass），其次密钥，最后原生 ssh
  if [ -n "$REMOTE_PASS" ]; then
    SSH_BASE="sshpass -p '$REMOTE_PASS' ssh $BASE_OPTS"
    SCP_BASE="sshpass -p '$REMOTE_PASS' scp $BASE_OPTS"
  elif [ -n "$REMOTE_SSH_KEY" ] && [ -f "$REMOTE_SSH_KEY" ]; then
    SSH_BASE="ssh -i $REMOTE_SSH_KEY $BASE_OPTS"
    SCP_BASE="scp -i $REMOTE_SSH_KEY $BASE_OPTS"
  else
    SSH_BASE="ssh $BASE_OPTS"
    SCP_BASE="scp $BASE_OPTS"
  fi
  SSH_CMD="eval $SSH_BASE ${REMOTE_USER}@${REMOTE_HOST}"
  SCP_CMD="eval $SCP_BASE"

  echo ""
  echo "📤 Step 5: 远程推送 → ${REMOTE_USER}@${REMOTE_HOST} (action: ${REMOTE_ACTION})"

  # ---- 5a. 检测远程架构 ----
  echo "  🔍 检测远程架构..."
  REMOTE_ARCH="linux-amd64"
  REMOTE_OS="Linux"
  if $SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" "uname -a" > /dev/null 2>&1; then
    REMOTE_ARCH_RAW=$($SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" "uname -m" 2>/dev/null | tr -d '\r')
    REMOTE_OS_RAW=$($SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" "uname -s" 2>/dev/null | tr -d '\r')
    case "$REMOTE_ARCH_RAW" in
      aarch64|arm64) REMOTE_ARCH="linux-arm64" ;;
      x86_64|amd64)  REMOTE_ARCH="linux-amd64" ;;
      *)             echo "  ⚠️  未知架构: $REMOTE_ARCH_RAW, 默认 linux-amd64" ;;
    esac
    REMOTE_OS="${REMOTE_OS_RAW}"
    echo "  ✅ ${REMOTE_USER}@${REMOTE_HOST} → ${REMOTE_OS} ${REMOTE_ARCH_RAW} (${REMOTE_ARCH})"
  else
    echo "  ❌ SSH 连接失败，请检查密码和网络"
    exit 1
  fi

  # ---- 5b. 找对应的二进制 ----
  src=$(find_binary "$REMOTE_ARCH") || true
  if [ -z "$src" ]; then
    echo "  ❌ 没有 ${REMOTE_ARCH} 的编译产物"
    echo "     先执行: bash scripts/build_all.sh"
    exit 1
  fi
  SRC_SIZE=$(stat -c%s "$src" 2>/dev/null || echo "0")
  SRC_SIZE_MB=$(awk "BEGIN{printf \"%.1f\", $SRC_SIZE/1024/1024}")
  echo "  📦 二进制: $src (${SRC_SIZE_MB}MB)"

  # ---- 5c. 推送二进制 (先传，避免停旧后断连) ----
  echo "  📄 SCP 传输中..."
  $SCP_BASE "$src" "${REMOTE_USER}@${REMOTE_HOST}:~/computehub-v${VERSION}" 2>/dev/null
  $SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" \
    "cp ~/computehub-v${VERSION} ~/computehub && chmod +x ~/computehub" 2>/dev/null

  # 验证远程文件（不阻塞，如果 SSH 后面断了也不影响）
  if $SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" "stat -c%s ~/computehub 2>/dev/null | tr -d '\n'" 2>/dev/null | grep -q .; then
    REMOTE_SIZE=$($SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" "stat -c%s ~/computehub 2>/dev/null" 2>/dev/null | tr -d '\r')
    if [ "$REMOTE_SIZE" = "$SRC_SIZE" ]; then
      echo "  ✅ 传输验证通过 (远程: $(awk "BEGIN{printf \"%.1f\", $REMOTE_SIZE/1024/1024}")MB)"
    else
      echo "  ⚠️  大小不匹配: 本地=${SRC_SIZE} vs 远程=${REMOTE_SIZE}，可能传输损坏"
    fi
  else
    echo "  ⚠️  SSH 验证超时（传输可能已完成）"
  fi

  # ---- 5d. 安装到 PATH ----
  echo "  🔧 安装到 PATH 并验证版本..."
  VERSION_CHECK=$($SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" \
    "B=/usr/local/bin; [ -d /data/data/com.termux/files/usr/bin ] && B=/data/data/com.termux/files/usr/bin; cp ~/computehub \$B/computehub; chmod +x \$B/computehub; \$B/computehub version" 2>/dev/null)
  if [ -n "$VERSION_CHECK" ]; then
    echo "     ✅ $VERSION_CHECK"
  else
    echo "     ⚠️  PATH 安装完成但版本验证超时"
  fi

  # ---- 5e. 停旧进程 + 启动新进程（合并为一条 SSH 命令，原子化） ----
  if [ "$REMOTE_ACTION" = "restart-all" ]; then
    echo "  🔄 重启所有服务（停旧→启动新）..."
    RESULT=$($SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" \
      "pkill -f 'computehub gateway' 2>/dev/null || true; \
       pkill -f 'computehub worker' 2>/dev/null || true; \
       sleep 1; \
       NODE_ID=\$(hostname)-worker; \
       nohup ~/computehub gateway --port 8282 > /tmp/gateway.log 2>&1 & \
       sleep 1; \
       nohup ~/computehub worker --gw ${REMOTE_GW} --node-id \${NODE_ID} --interval 3 --concurrent 8 > /tmp/worker.log 2>&1 & \
       echo 'GW_PID: '; pgrep -f 'computehub gateway' | head -1; \
       echo 'WK_PID: '; pgrep -f 'computehub worker' | head -1" 2>/dev/null)
    if echo "$RESULT" | grep -q "GW_PID"; then
      echo "     ✅ Gateway PID: $(echo "$RESULT" | grep GW_PID | awk '{print $2}')"
      echo "     ✅ Worker PID: $(echo "$RESULT" | grep WK_PID | awk '{print $2}')"
      sleep 2
      curl -s --connect-timeout 5 "${REMOTE_GW}/api/health" 2>/dev/null | grep -qi "healthy\|success" \
        && echo "     ✅ Gateway 健康检查通过" \
        || echo "     ⚠️  Gateway 暂时未响应（可能需稍等）"
    else
      echo "     ⚠️  服务已重启，但 SSH 连接已断开"
      echo "     📍 Gateway 应该已恢复: ${REMOTE_GW}"
    fi

  elif [ "$REMOTE_ACTION" = "gateway" ]; then
    echo "  🚀 启动新 Gateway..."
    $SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" \
      "pkill -f 'computehub gateway' 2>/dev/null || true; sleep 1; \
       nohup ~/computehub gateway --port 8282 > /tmp/gateway.log 2>&1 & \
       sleep 2 && echo '✅ PID: ' \$(pgrep -f 'computehub gateway' | head -1)" 2>/dev/null
    sleep 2
    curl -s --connect-timeout 5 "${REMOTE_GW}/api/health" 2>/dev/null | grep -qi "healthy\|success" \
      && echo "     ✅ Gateway 健康检查通过" \
      || echo "     ⚠️  Gateway 暂时未响应"

  elif [ "$REMOTE_ACTION" = "worker" ]; then
    NODE_ID="$($SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" "hostname" 2>/dev/null | tr -d '\r')-worker"
    echo "  🚀 启动新 Worker (node-id: ${NODE_ID})..."
    $SSH_BASE "${REMOTE_USER}@${REMOTE_HOST}" \
      "pkill -f 'computehub worker' 2>/dev/null || true; sleep 1; \
       nohup ~/computehub worker --gw ${REMOTE_GW} --node-id ${NODE_ID} --interval 3 --concurrent 8 > /tmp/worker.log 2>&1 & \
       sleep 2 && echo '✅ PID: ' \$(pgrep -f 'computehub worker' | head -1)" 2>/dev/null
    sleep 2
    curl -s --connect-timeout 5 "${REMOTE_GW}/api/v1/nodes" 2>/dev/null | grep -qi "${NODE_ID}" \
      && echo "     ✅ Worker 已注册到 Gateway" \
      || echo "     ⚠️  Worker 注册未确认"
  fi

  echo ""
  echo "  ✅ 远程推送完成! (v${VERSION} → ${REMOTE_ARCH})"
  echo "    远程文件: ~/computehub (最新)  ~/computehub-v${VERSION} (版本存档)"
  if [ "$REMOTE_ACTION" != "none" ]; then
    echo "    已启动: ${REMOTE_ACTION}"
    echo "    日志: /tmp/gateway.log  /tmp/worker.log"
  fi
fi

# ---- 5g. 上传 Gallery（给其他节点下载） ----
echo ""
echo "📤 Step 6: Gallery 上传 (供其他 Worker 下载)"
GALLERY_URL="${GATEWAY_GALLERY_URL:-http://36.250.122.43:8282}"

# 平台 → Gallery 文件名映射（固定名称，避免后端冲突重命名加时间戳）
declare -A GALLERY_NAMES
GALLERY_NAMES["linux-amd64"]="computehub-linux-amd64"
GALLERY_NAMES["linux-arm64"]="computehub-linux-arm64"
GALLERY_NAMES["windows-amd64"]="computehub-windows-amd64.exe"

for plat in linux-amd64 linux-arm64 windows-amd64; do
  src_bin=$(find_binary "$plat") || continue
  gallery_name="${GALLERY_NAMES[$plat]}"
  echo "  📦 ${plat} → ${gallery_name}..."

  # 先删旧的（避免 Gallery 追加时间戳重命名）
  curl -s --connect-timeout 3 -X POST \
    "${GALLERY_URL}/api/v1/gallery/delete?name=${gallery_name}" > /dev/null 2>&1 || true

  # 上传时通过 filename= 指定固定名称
  TEMP_LINK=$(mktemp)
  cp "$src_bin" "$TEMP_LINK"
  RESP=$(curl -s --connect-timeout 5 \
    -F "file=@${TEMP_LINK};filename=${gallery_name}" \
    "${GALLERY_URL}/api/v1/gallery/upload" 2>/dev/null)
  rm -f "$TEMP_LINK"

  if echo "$RESP" | grep -q '"success":true'; then
    echo "     ✅ 已上传: ${GALLERY_URL}/api/v1/files/${gallery_name}"
  else
    echo "     ⚠️  Gallery 上传失败（Gateway 可能未运行）"
  fi
done

echo ""
echo "✅ 全部完成! v${VERSION}"
echo ""
echo "💡 其他节点 wget 下载:"
echo "   wget -O computehub ${GALLERY_URL}/api/v1/files/computehub-linux-arm64  (ARM64)"
echo "   wget -O computehub ${GALLERY_URL}/api/v1/files/computehub-linux-amd64  (AMD64)"
