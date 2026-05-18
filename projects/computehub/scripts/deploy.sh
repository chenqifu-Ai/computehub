#!/bin/bash
# ============================================================
# deploy.sh — ComputeHub 部署统一入口
# 对齐 STD-CONFIG-001 v1.1
#
# 用法:
#   deploy.sh build [version]              # 编译全平台
#   deploy.sh deploy <host> [args]         # build + SSH 部署
#   deploy.sh push <host> [args]           # 仅推送二进制（不 build）
#   deploy.sh upgrade <node_id>            # 通过 Task 升级 Worker
#
# 示例:
#   bash scripts/deploy.sh build
#   bash scripts/deploy.sh deploy 36.250.122.43
#   bash scripts/deploy.sh push 36.250.122.43 --restart
#   bash scripts/deploy.sh push 192.168.2.140 --user chenqifu --password 'xxx' --port 8022
#   bash scripts/deploy.sh upgrade gpu-01
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
BIN_DIR="${PROJECT_DIR}/bin"
DEPLOY_DIR="${PROJECT_DIR}/deploy"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()  { echo -e "  ${GREEN}${1}${NC}"; }
warn(){ echo -e "  ${YELLOW}${1}${NC}"; }
err() { echo -e "  ${RED}${1}${NC}"; }

# ── 工具函数 ──────────────────────────────────────────────

get_version() {
  grep 'VERSION = "' src/version/version.go | awk -F'"' '{print $2}'
}

get_platform() {
  local os arch
  os=$(uname -s | tr '[:upper:]' '[:lower:]')
  arch=$(uname -m)
  case "$arch" in
    aarch64|arm64)  arch="arm64" ;;
    x86_64|amd64)   arch="amd64" ;;
  esac
  echo "${os}-${arch}"
}

find_binary() {
  # find_binary <platform> — 返回二进制路径，从近到远
  local platform="$1"
  local os="${platform%%-*}"
  local ext=""; [ "$os" = "windows" ] && ext=".exe"

  for dir in "${BIN_DIR}" "${DEPLOY_DIR}/$(get_version)" "${DEPLOY_DIR}"; do
    local f="${dir}/${platform}/computehub${ext}"
    [ -f "$f" ] && { echo "$f"; return 0; }
  done
  return 1
}

detect_remote_arch() {
  # detect_remote_arch <ssh_cmd> → linux-arm64|linux-amd64
  local ssh_cmd=$1
  local rem_arch=$($ssh_cmd "uname -m" 2>/dev/null | tr -d '\r')
  case "$rem_arch" in
    aarch64|arm64) echo "linux-arm64" ;;
    x86_64|amd64)  echo "linux-amd64" ;;
    *)             echo "linux-amd64" ;;
  esac
}

# ── 编译 ──────────────────────────────────────────────────

cmd_build() {
  local version="${1:-$(get_version)}"
  echo "🔨 ComputeHub v${version} 全平台编译"
  echo "================================="

  go version >/dev/null 2>&1 || { err "Go 未安装"; exit 1; }

  mkdir -p "$BIN_DIR"

  # 按 STD-CONFIG-001 §1.2 编译命令规范
  # 按 STD-CONFIG-001 §1.2: -s -w strip 调试符号, BUILD 注入时间戳
  local ldflags="-s -w -X github.com/computehub/opc/src/version.BUILD=$(date +%s)"
  local total=0 pass=0 fail=0

  for entry in "linux/amd64:linux-amd64" "linux/arm64:linux-arm64" \
               "darwin/amd64:darwin-amd64" "darwin/arm64:darwin-arm64" \
               "windows/amd64:windows-amd64"; do
    IFS=':' read -r go_target platform <<< "$entry"
    IFS='/' read -r goos goarch <<< "$go_target"

    local ext=""; [ "$goos" = "windows" ] && ext=".exe"
    local out="${BIN_DIR}/${platform}/computehub${ext}"
    local tmp="${out}.tmp"
    total=$((total + 1))

    printf "  [%d/5] %s ... " "$total" "$platform"

    if CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch" \
         go build -ldflags="$ldflags" -o "$tmp" "./cmd/computehub/" 2>/dev/null; then
      mkdir -p "$(dirname "$out")"
      mv "$tmp" "$out"
      chmod +x "$out" 2>/dev/null || true
      local size=$(stat -c%s "$out" 2>/dev/null || echo "0")
      local mb=$(awk "BEGIN{printf \"%.1f\", $size/1024/1024}")
      echo "✅ ${mb} MB"
      pass=$((pass + 1))
    else
      rm -f "$tmp"
      echo "❌ 失败"
      fail=$((fail + 1))
    fi
  done

  echo "================================="
  echo "结果: ${pass}/${total} 通过, ${fail} 失败"

  # 同步到 deploy/ 平铺目录
  cmd_sync

  echo "✅ 编译完成! v${version}"
  echo "   ${BIN_DIR}/{platform}/computehub"
  echo "   ${DEPLOY_DIR}/{platform}/computehub"
  echo ""
  echo "💡 快速部署: bash scripts/deploy.sh push <host>"
}

# ── 同步到 deploy/ ───────────────────────────────────────

cmd_sync() {
  local version=$(get_version)
  local cur_plat=$(get_platform)

  mkdir -p "$DEPLOY_DIR"

  # 平铺到 deploy/{platform}/
  for plat_dir in linux-amd64 linux-arm64 darwin-amd64 darwin-arm64 windows-amd64; do
    local os="${plat_dir%%-*}"
    local ext=""; [ "$os" = "windows" ] && ext=".exe"
    local src
    src=$(find_binary "$plat_dir") || continue
    mkdir -p "${DEPLOY_DIR}/${plat_dir}"
    cp "$src" "${DEPLOY_DIR}/${plat_dir}/computehub${ext}"
    chmod +x "${DEPLOY_DIR}/${plat_dir}/computehub${ext}" 2>/dev/null || true
  done

  # 当前平台到根目录
  local ext=""; [[ "$cur_plat" == windows-* ]] && ext=".exe"
  local src
  src=$(find_binary "$cur_plat") || true
  if [ -n "$src" ]; then
    cp "$src" "${DEPLOY_DIR}/computehub${ext}"
    chmod +x "${DEPLOY_DIR}/computehub${ext}" 2>/dev/null || true
  fi

  # sha256sums
  cd "$DEPLOY_DIR"
  find . -type f \( -name "computehub" -o -name "computehub.exe" \) | sort \
    | xargs sha256sum > "sha256sums-${version}.txt" 2>/dev/null || true
  cd "$PROJECT_DIR"

  echo "$version" > "${DEPLOY_DIR}/version.txt"
  ok "同步完成 → deploy/"
}

# ── SSH 推送 ──────────────────────────────────────────────

cmd_push() {
  local host="" user="computehub" port="22" password=""
  local action="none" version="" gateway="" node_id=""

  # 解析参数
  host="$1"; shift
  while [ $# -gt 0 ]; do
    case "$1" in
      --user|-u)     shift; user="$1" ;;
      --password|-p) shift; password="$1" ;;
      --port|-P)     shift; port="$1" ;;
      --action|-a)   shift; action="$1" ;;   # restart|gateway|worker|none
      --version)     shift; version="$1" ;;
      --gateway|-g)  shift; gateway="$1" ;;
      --node-id)     shift; node_id="$1" ;;
      *) err "未知参数: $1"; exit 1 ;;
    esac
    shift
  done

  [ -z "$host" ] && { err "缺少目标主机"; exit 1; }
  version="${version:-$(get_version)}"
  gateway="${gateway:-http://${host}:8282}"
  node_id="${node_id:-$(hostname)-worker}"

  # SSH base command
  local ssh_opts="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -p ${port}"
  if [ -n "$password" ]; then
    SSH="sshpass -p '${password}' ssh ${ssh_opts}"
    SCP="sshpass -p '${password}' scp ${ssh_opts}"
  else
    SSH="ssh ${ssh_opts}"
    SCP="scp ${ssh_opts}"
  fi
  SSH_CMD="eval ${SSH} ${user}@${host}"
  SCP_CMD="eval ${SCP}"

  echo "📤 推送 ComputeHub v${version} → ${user}@${host}:${port}"
  echo "   目标: ${action}"

  # 1. 连接 + 架构检测
  echo "  🔍 连接检测..."
  $SSH_CMD "uname -a" >/dev/null 2>&1 || { err "SSH 连接失败"; exit 1; }
  local remote_arch
  remote_arch=$(detect_remote_arch "$SSH_CMD")
  ok "已连接 (${remote_arch})"

  # 2. 找二进制
  local src
  src=$(find_binary "$remote_arch") || { err "无 ${remote_arch} 编译产物，先: bash scripts/deploy.sh build"; exit 1; }
  local src_size=$(stat -c%s "$src" 2>/dev/null || echo "0")
  local src_mb=$(awk "BEGIN{printf \"%.1f\", $src_size/1024/1024}")
  echo "  📦 ${src} (${src_mb} MB)"

  # 3. SCP 传输
  echo "  ⬆️ 传输中..."
  $SCP_CMD "$src" "${user}@${host}:~/computehub-v${version}" 2>/dev/null
  $SSH_CMD "cp ~/computehub-v${version} ~/computehub && chmod +x ~/computehub" 2>/dev/null

  # 4. 验证传输
  local rem_size
  rem_size=$($SSH_CMD "stat -c%s ~/computehub 2>/dev/null" 2>/dev/null | tr -d '\r' || echo "0")
  if [ "$rem_size" = "$src_size" ]; then
    ok "传输验证通过 ($(awk "BEGIN{printf \"%.1f\", $rem_size/1024/1024}") MB)"
  else
    warn "大小不匹配: 本地=${src_size} vs 远程=${rem_size}"
  fi

  # 5. 安装到 PATH
  $SSH_CMD "B=/usr/local/bin; [ -d /data/data/com.termux/files/usr/bin ] && B=/data/data/com.termux/files/usr/bin; \
             cp ~/computehub \$B/computehub; chmod +x \$B/computehub; \$B/computehub version" 2>/dev/null \
    && ok "已安装到 PATH" || warn "PATH 安装可能未完成"

  # 6. 执行动作
  case "$action" in
    restart)
      echo "  🔄 重启所有服务..."
      $SSH_CMD "pkill -f 'computehub gateway' 2>/dev/null || true; \
                 pkill -f 'computehub worker' 2>/dev/null || true; \
                 sleep 1; \
                 nohup ~/computehub gateway --port 8282 > /tmp/gateway.log 2>&1 & \
                 sleep 1; \
                 nohup ~/computehub worker --gw ${gateway} --node-id ${node_id} --interval 3 --concurrent 8 > /tmp/worker.log 2>&1 & \
                 echo '✅ 服务已启动'" 2>/dev/null || true
      sleep 2
      curl -s --connect-timeout 5 "${gateway}/api/health" 2>/dev/null | grep -qi "healthy\|success" \
        && ok "Gateway 健康检查通过" || warn "Gateway 未响应"
      ;;
    gateway)
      echo "  🚀 启动 Gateway..."
      $SSH_CMD "pkill -f 'computehub gateway' 2>/dev/null || true; sleep 1; \
                 nohup ~/computehub gateway --port 8282 > /tmp/gateway.log 2>&1 &" 2>/dev/null || true
      sleep 2
      curl -s --connect-timeout 5 "${gateway}/api/health" 2>/dev/null | grep -qi "healthy\|success" \
        && ok "Gateway 启动成功" || warn "Gateway 未响应"
      ;;
    worker)
      echo "  🚀 启动 Worker..."
      $SSH_CMD "pkill -f 'computehub worker' 2>/dev/null || true; sleep 1; \
                 nohup ~/computehub worker --gw ${gateway} --node-id ${node_id} --interval 3 --concurrent 8 > /tmp/worker.log 2>&1 &" 2>/dev/null || true
      sleep 2
      $SSH_CMD "pgrep -f 'computehub worker'" >/dev/null 2>&1 \
        && ok "Worker 已启动" || warn "Worker 可能未启动"
      ;;
    none) ;;
  esac

  echo ""
  ok "推送完成! v${version} → ${remote_arch}"
  if [ "$action" != "none" ]; then
    echo "   动作: ${action}"
    echo "   远程文件: ~/computehub (最新)  ~/computehub-v${version} (存档)"
  fi
}

# ── 部署（build + push） ──────────────────────────────────

cmd_deploy() {
  local host="$1"; shift
  cmd_build
  cmd_push "$host" "$@"
}

# ── 远程升级（通过 Gateway Task） ─────────────────────────

cmd_upgrade() {
  local target_node="${1:-}"
  local gw="${GATEWAY_URL:-http://localhost:8282}"

  if [ -z "$target_node" ]; then
    # 升级所有在线节点
    echo "🔧 升级所有在线节点..."
    bash "$(dirname "$0")/upgrade.sh" "$gw"
    return $?
  fi

  echo "🔧 升级节点: ${target_node}"
  bash "$(dirname "$0")/upgrade.sh" "$gw" "$target_node"
}

# ── Gallery 上传 ─────────────────────────────────────────

cmd_gallery_upload() {
  bash "$(dirname "$0")/gallery-upload.sh"
}

# ── Main ──────────────────────────────────────────────────

usage() {
  echo "ComputeHub 部署工具 (STD-CONFIG-001)"
  echo ""
  echo "用法:"
  echo "  bash scripts/deploy.sh build [version]              # 编译"
  echo "  bash scripts/deploy.sh deploy <host> [args]         # build + 部署"
  echo "  bash scripts/deploy.sh push <host> [args]           # 仅推送"
  echo "  bash scripts/deploy.sh upgrade [node_id]            # Task 升级"
  echo "  bash scripts/deploy.sh sync                         # 同步到 deploy/"
  echo "  bash scripts/deploy.sh gallery-upload               # Gallery 上传"
  echo ""
  echo "push/deploy 参数:"
  echo "  --user|-u <name>        SSH 用户 (默认: computehub)"
  echo "  --password|-p <pass>    SSH 密码 (默认: 密钥)"
  echo "  --port|-P <port>        SSH 端口 (默认: 22)"
  echo "  --action|-a <action>    推送后动作: restart|gateway|worker|none (默认: none)"
  echo "  --gateway|-g <url>      Gateway 地址 (默认: http://<host>:8282)"
  echo "  --node-id <id>          Worker 节点 ID (默认: hostname-worker)"
  echo "  --version <ver>         指定版本"
  echo ""
  echo "示例:"
  echo "  bash scripts/deploy.sh build"
  echo "  bash scripts/deploy.sh deploy 36.250.122.43 --action restart"
  echo "  bash scripts/deploy.sh push 192.168.2.140 --user chenqifu --password '123' --port 8022"
  echo "  bash scripts/deploy.sh upgrade worker-ecs-p2ph"
}

CMD="${1:-help}"; [ $# -gt 0 ] && shift

case "$CMD" in
  build)      cmd_build "$@" ;;
  deploy)     [ $# -ge 1 ] && cmd_deploy "$@" || usage ;;
  push)       [ $# -ge 1 ] && cmd_push "$@" || usage ;;
  upgrade)    cmd_upgrade "$@" ;;
  sync)       cmd_sync ;;
  gallery-upload) cmd_gallery_upload ;;
  help|--help|-h) usage ;;
  *)          err "未知命令: $CMD"; usage; exit 1 ;;
esac
