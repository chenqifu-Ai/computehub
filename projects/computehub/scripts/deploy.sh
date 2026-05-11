#!/bin/bash
# ============================================================
# ComputeHub 一键部署脚本
# 用法:
#   本地构建:      bash scripts/deploy.sh build [版本号]
#   远程部署:      bash scripts/deploy.sh deploy <目标IP> [密码] [--component 组件]
#   本地构建+部署: bash scripts/deploy.sh all <目标IP> [密码] [版本号]
#
# 示例:
#   bash scripts/deploy.sh build 0.7.5
#   bash scripts/deploy.sh deploy 192.168.2.165 'mypass' --component worker
#   bash scripts/deploy.sh all 192.168.2.140 'c9fc9f,.' 0.7.5
#
# 环境变量:
#   GATEWAY_ADDR   - Worker 连接的 Gateway 地址 (默认: 目标IP:8282)
#   NODE_ID        - Worker 节点 ID (默认: cqf-{hostname})
#   REGION         - Worker 区域 (默认: cn-east)
# ============================================================
set -euo pipefail

# ---- 配置 ----
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${PROJECT_DIR}/bin"
DEPLOY_DIR="${PROJECT_DIR}/deploy"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"

# 组件的平台映射
declare -A PLATFORM_OS_ARCH
PLATFORM_OS_ARCH["linux-amd64"]="linux/amd64"
PLATFORM_OS_ARCH["linux-arm64"]="linux/arm64"
PLATFORM_OS_ARCH["windows-amd64"]="windows/amd64"
PLATFORM_OS_ARCH["darwin-amd64"]="darwin/amd64"
PLATFORM_OS_ARCH["darwin-arm64"]="darwin/arm64"

COMPONENTS=("gateway" "tui" "worker" "node")

# ---- 颜色 ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()  { echo -e "  ${GREEN}✅${NC} $1"; }
info(){ echo -e "  ${CYAN}ℹ️${NC}  $1"; }
warn(){ echo -e "  ${YELLOW}⚠️${NC}  $1"; }
err() { echo -e "  ${RED}❌${NC}  $1"; }

# ---- 辅助函数 ----
usage() {
  sed -n '3,14p' "$0"
  exit 1
}

get_version() {
  cat "${PROJECT_DIR}/deploy/version.txt" 2>/dev/null || echo "0.0.0"
}

ssh_exec() {
  local host="$1" pass="$2"; shift 2
  if [ -n "$pass" ]; then
    sshpass -p "$pass" ssh $SSH_OPTS "root@${host}" "$@" 2>&1 | grep -v "WARNING:.*post-quantum"
  else
    ssh $SSH_OPTS "root@${host}" "$@" 2>&1 | grep -v "WARNING:.*post-quantum"
  fi
}

scp_file() {
  local host="$1" pass="$2" src="$3" dst="$4"
  if [ -n "$pass" ]; then
    sshpass -p "$pass" scp $SSH_OPTS "$src" "root@${host}:${dst}" 2>&1 | grep -v "WARNING:"
  else
    scp $SSH_OPTS "$src" "root@${host}:${dst}" 2>&1 | grep -v "WARNING:"
  fi
}

# ============================================================
# Step 1: 构建 (Build)
# ============================================================
cmd_build() {
  local version="${1:-$(get_version)}"
  local ldflags="-s -w -X github.com/computehub/opc/src/version.VERSION=${version}"

  echo ""
  echo "========================================"
  echo "  🔨 ComputeHub v${version} 全平台构建"
  echo "========================================"
  echo ""

  # 切换到项目根目录
  cd "${PROJECT_DIR}"

  # 检查 Go
  go version || { err "Go 未安装"; exit 1; }

  rm -rf "${BIN_DIR}"/*/
  mkdir -p "${BIN_DIR}"

  for platform in "${!PLATFORM_OS_ARCH[@]}"; do
    IFS='/' read -r goos goarch <<< "${PLATFORM_OS_ARCH[$platform]}"
    ext=""
    [ "$goos" = "windows" ] && ext=".exe"

    plat_dir="${BIN_DIR}/${platform}"
    mkdir -p "$plat_dir"

    echo "  📦 ${CYAN}${platform}${NC}"

    for comp in "${COMPONENTS[@]}"; do
      output="${plat_dir}/computehub-${comp}${ext}"
      src_path="./cmd/${comp}/"
      [ "$comp" = "node" ] && src_path="./cmd/node/"

      # 检查源目录是否存在
      if [ ! -d "$src_path" ]; then
        warn "${comp}: 源目录 ${src_path} 不存在，跳过"
        continue
      fi

      echo -n "    ${comp}... "
      if CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch" go build $ldflags \
        -o "$output" "$src_path" 2>/dev/null; then
        size=$(ls -lh "$output" | awk '{print $5}')
        echo -e "${GREEN}✅ ${size}${NC}"
      else
        echo -e "${RED}❌${NC}"
      fi
    done
    echo ""
  done

  # 验证
  echo "  ${CYAN}构建产物:${NC}"
  find "${BIN_DIR}" -type f -name "computehub-*" | sort | while read f; do
    echo "    $(ls -lh "$f" | awk '{print $5}')  ${f#${BIN_DIR}/}"
  done

  # 更新 deploy/
  echo ""
  cmd_sync_deploy "$version"

  echo ""
  ok "构建完成: v${version}"
}

# ============================================================
# Step 2: 同步 deploy/ 目录
# ============================================================
cmd_sync_deploy() {
  local version="${1:-$(get_version)}"
  echo "  📤 同步到 deploy/ ..."

  mkdir -p "${DEPLOY_DIR}/archive"

  # 归档旧文件
  for f in "${DEPLOY_DIR}"/computehub-*; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    if [ -f "${BIN_DIR}/linux-arm64/${base}" ] || [ -f "${BIN_DIR}/linux-amd64/${base}" ] || \
       [ -f "${BIN_DIR}/windows-amd64/${base}.exe" ] || [ -f "${BIN_DIR}/darwin-amd64/${base}" ] || \
       [ -f "${BIN_DIR}/darwin-arm64/${base}" ]; then
      # 旧文件会被覆盖，归档
      mkdir -p "${DEPLOY_DIR}/archive/v${version}-pre/"
      cp "$f" "${DEPLOY_DIR}/archive/v${version}-pre/"
      info "已归档旧文件: ${base}"
    fi
  done

  # 复制新构建到 deploy/
  for platform in "${!PLATFORM_OS_ARCH[@]}"; do
    plat_dir="${BIN_DIR}/${platform}"
    for f in "${plat_dir}"/*; do
      [ -f "$f" ] || continue
      base=$(basename "$f")
      # 带平台后缀的文件名: computehub-gateway-linux-amd64
      target="${DEPLOY_DIR}/${base%-${platform}}"
      # 如果已经有同名文件则加平台后缀
      if [ -f "${DEPLOY_DIR}/${base}" ]; then
        cp "$f" "${DEPLOY_DIR}/${base}"
      else
        cp "$f" "${DEPLOY_DIR}/${base}"
      fi
    done
  done

  # 直接复制全部到 deploy/（用平台感知命名）
  for platform in "${!PLATFORM_OS_ARCH[@]}"; do
    IFS='/' read -r goos goarch <<< "${PLATFORM_OS_ARCH[$platform]}"
    ext=""; [ "$goos" = "windows" ] && ext=".exe"
    suffix="${goos}-${goarch}${ext}"

    for comp in "${COMPONENTS[@]}"; do
      src="${BIN_DIR}/${platform}/computehub-${comp}${ext}"
      [ -f "$src" ] || continue
      dst="${DEPLOY_DIR}/computehub-${comp}-${suffix}"
      chmod +x "$src"
      cp "$src" "$dst"
      ok "${dst}"
    done
  done

  # 更新版本文件和 SHA256
  echo "${version}" > "${DEPLOY_DIR}/version.txt"

  cd "${DEPLOY_DIR}"
  echo "# ComputeHub v${version} SHA256 ($(date +%Y-%m-%d))" > sha256sums-v${version}.txt
  for f in computehub-*; do
    [ -f "$f" ] || continue
    echo "$(sha256sum "$f" | cut -d' ' -f1)  $f" >> "sha256sums-v${version}.txt"
  done
  cd "${PROJECT_DIR}"

  ok "deploy/ 已同步 (v${version})"
}

# ============================================================
# Step 3: 远程部署
# ============================================================
cmd_deploy() {
  local host="${1:?缺少目标 IP}"
  local pass="${2:-}"
  local component="${3:-all}"
  local version="${4:-$(get_version)}"
  local gateway_addr="${GATEWAY_ADDR:-${host}:8282}"
  local node_id="${NODE_ID:-cqf-${host##*.}}"
  local region="${REGION:-cn-east}"

  echo ""
  echo "========================================"
  echo "  📡 远程部署到 ${host}"
  echo "  组件:     ${component}"
  echo "  版本:     v${version}"
  echo "  Gateway:  ${gateway_addr}"
  echo "  Node ID:  ${node_id}"
  echo "========================================"
  echo ""

  # 检查可用性
  echo "  🔍 检查 ${host} ..."
  if ! ping -c 1 -W 3 "$host" >/dev/null 2>&1; then
    err "主机 ${host} 不可达"
    exit 1
  fi
  ok "主机可达"

  # SSH 可用性
  if ssh_exec "$host" "$pass" "uname -a" >/dev/null 2>&1; then
    os_info=$(ssh_exec "$host" "$pass" "uname -s" 2>/dev/null || echo "unknown")
    arch_info=$(ssh_exec "$host" "$pass" "uname -m" 2>/dev/null || echo "unknown")
    ok "SSH 连接成功: ${os_info} ${arch_info}"
  else
    err "SSH 连接失败（需配置 sshpass 或 SSH key）"
    exit 1
  fi

  # 确定目标平台
  platform=""
  case "${os_info},${arch_info}" in
    Linux,x86_64|Linux,amd64)  platform="linux-amd64" ;;
    Linux,aarch64|Linux,arm64) platform="linux-arm64" ;;
    *Windows*|*windows*,*)     platform="windows-amd64" ;;
    *) warn "未知平台: ${os_info}/${arch_info}，尝试 linux-amd64"; platform="linux-amd64" ;;
  esac

  # 需要部署的组件列表
  local components_to_deploy=()
  if [ "$component" = "all" ]; then
    comp_targets=("gateway" "tui" "worker" "node")
  else
    comp_targets=("$component")
  fi

  echo ""
  echo "  📦 传输文件..."

  for comp in "${comp_targets[@]}"; do
    ext=""; [[ "$platform" == windows-* ]] && ext=".exe"
    src="${DEPLOY_DIR}/computehub-${comp}-${platform}${ext}"
    dst="~/computehub-${comp}${ext}"

    if [ ! -f "$src" ]; then
      # 回退到 bin/ 目录查找
      src="${BIN_DIR}/${platform}/computehub-${comp}${ext}"
      [ -f "$src" ] || { err "找不到 ${comp} 二进制"; continue; }
    fi

    scp_file "$host" "$pass" "$src" "$dst" && ok "传输 ${comp} (${src##*/})" || err "传输 ${comp} 失败"
  done

  # 安装 & 启动
  echo ""
  echo "  🚀 安装 & 启动..."

  # 安装
  install_cmd=""
  if [[ "$platform" == windows-* ]]; then
    # Windows - copy to Program Files (placeholder, WinRM/SMB needed)
    warn "Windows 自动部署暂仅支持文件传输，需手动安装"
  else
    # Linux - chmod +x, 创建 systemd service
    install_cmd=$(cat <<'SCRIPT'
set -e
SCRIPT
)

    for comp in "${comp_targets[@]}"; do
      ext=""; [[ "$platform" == windows-* ]] && ext=".exe"
      bin_path="~/computehub-${comp}${ext}"

      install_cmd+="
echo '  安装 ${comp}...'
chmod +x ${bin_path} 2>/dev/null
sudo cp ${bin_path} /usr/local/bin/computehub-${comp} 2>/dev/null && echo '    ✅ 复制到 /usr/local/bin/' || echo '    ⚠️  sudo 不可用，留在 ~/'
"
    done

    # 创建 Gateway systemd service
    if [[ " ${comp_targets[*]} " =~ " gateway " ]]; then
      install_cmd+="
echo '  配置 Gateway systemd service...'
cat > /tmp/computehub-gateway.service << 'SERVICE'
[Unit]
Description=ComputeHub Gateway
After=network.target

[Service]
ExecStart=/usr/local/bin/computehub-gateway
Restart=always
RestartSec=5
User=$(whoami)

[Install]
WantedBy=multi-user.target
SERVICE
sudo mv /tmp/computehub-gateway.service /etc/systemd/system/ 2>/dev/null && sudo systemctl daemon-reload 2>/dev/null || echo '    ⚠️  systemd 不可用'
"
    fi

    # 启动 Worker
    if [[ " ${comp_targets[*]} " =~ " worker " ]]; then
      # 先停旧 worker
      install_cmd+="
echo '  停旧 worker...'
pkill -f 'computehub-worker' 2>/dev/null || true
sleep 1

echo '  启动 v${version} Worker...'
nohup ~/computehub-worker --gw ${gateway_addr} --node-id ${node_id} --region ${region} > /tmp/worker.log 2>&1 &
echo '    PID: '\$!''
echo '    日志: /tmp/worker.log'
"
    fi

    # 启动 Gateway
    if [[ " ${comp_targets[*]} " =~ " gateway " ]]; then
      install_cmd+="
echo '  停旧 Gateway...'
pkill -f 'computehub-gateway' 2>/dev/null || true
sleep 1

echo '  启动 v${version} Gateway...'
nohup ~/computehub-gateway > /tmp/gateway.log 2>&1 &
echo '    PID: '\$!''
echo '    日志: /tmp/gateway.log'
sleep 2
ss -tlnp 2>/dev/null | grep 8282 && echo '    ✅ 端口 :8282 监听中' || echo '    ⚠️  端口未就绪，检查日志'
"
    fi

    echo "$install_cmd" | ssh_exec "$host" "$pass" "bash -s"
  fi

  # 验证
  echo ""
  echo "  ✅ 验证..."
  if [[ " ${comp_targets[*]} " =~ " gateway " ]]; then
    local_check=$(curl -s --connect-timeout 5 "http://${host}:8282/api/health" 2>/dev/null || echo "{}")
    if echo "$local_check" | grep -q "Healthy"; then
      ok "Gateway health ✅"
    else
      warn "Gateway 响应: ${local_check:0:60}"
    fi
  fi

  if [[ " ${comp_targets[*]} " =~ " worker " ]]; then
    sleep 2
    worker_check=$(ssh_exec "$host" "$pass" "ps aux | grep computehub-worker | grep -v grep | head -1" 2>/dev/null || true)
    if [ -n "$worker_check" ]; then
      ok "Worker 运行中 ✅"
    else
      warn "Worker 进程未检测到"
    fi
  fi

  echo ""
  echo "========================================"
  ok "远程部署完成: ${host}"
  echo "  组件: ${comp_targets[*]}"
  echo "  Gateway: http://${gateway_addr}"
  echo "  Node:    ${node_id} (${region})"
  echo "========================================"
}

# ============================================================
# main
# ============================================================
cmd="${1:-help}"
shift || true

case "$cmd" in
  build)
    cmd_build "${1:-}"
    ;;
  sync|sync-deploy)
    cmd_sync_deploy "${1:-}"
    ;;
  deploy)
    host="${1:-}"; pass="${2:-}"; comp="${3:-all}"; ver="${4:-}"
    [ -z "$host" ] && usage
    cmd_deploy "$host" "$pass" "$comp" "$ver"
    ;;
  all)
    host="${1:-}"; pass="${2:-}"; ver="${3:-$(get_version)}"
    [ -z "$host" ] && usage
    cmd_build "$ver"
    cmd_deploy "$host" "$pass" "all" "$ver"
    ;;
  help|*)
    usage
    ;;
esac
