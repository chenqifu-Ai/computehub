#!/bin/bash
# ComputeHub 一键部署脚本
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${PROJECT_DIR}/bin"
DEPLOY_DIR="${PROJECT_DIR}/deploy"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()  { echo -e "  ${GREEN}$1${NC}"; }
warn(){ echo -e "  ${YELLOW}$1${NC}"; }
err() { echo -e "  ${RED}$1${NC}"; }

usage() {
  echo "Usage:"
  echo "  deploy.sh build [version]"
  echo "  deploy.sh deploy <host> [password] [--component X] [--port N] [--gateway URL] [--node-id X] [--region X]"
  echo "  deploy.sh all <host> [password] [--component X] [--port N] [--version V]"
  exit 1
}

get_version() { cat "${DEPLOY_DIR}/version.txt" 2>/dev/null || echo "0.0.0"; }

ssh_exec() {
  local host=$1 pass=$2 port=$3 user=$4; shift 4
  local cmd="ssh ${SSH_OPTS} -p ${port} ${user}@${host}"
  if [ -n "$pass" ]; then sshpass -p "$pass" $cmd "$@"
  else $cmd "$@"; fi
}

download_via_gateway() {
  local host=$1 pass=$2 port=$3 user=$4 comp=$5 platform=$6 gw=$7
  local ext=""; [[ "$platform" == windows-* ]] && ext=".exe"
  local file_url="${gw%/}/api/v1/download?file=computehub-${comp}-${platform}${ext}"
  local dst="~/computehub-${comp}${ext}"
  echo "  ${comp}: ${file_url}"
  ssh_exec "$host" "$pass" "$port" "$user" "curl -sL -o '${dst}' '${file_url}' && chmod +x '${dst}'"
  ssh_exec "$host" "$pass" "$port" "$user" "test -s '${dst}'" && ok "${comp} downloaded" || err "${comp} download failed"
}

cmd_build() {
  local version="${1:-$(get_version)}"
  echo "  Build v${version}"
  cd "${PROJECT_DIR}"
  go version || { err "Go not found"; exit 1; }
  declare -A MAP=( ["linux-amd64"]="linux/amd64" ["linux-arm64"]="linux/arm64" ["windows-amd64"]="windows/amd64" )
  local ldflags="-s -w -X github.com/computehub/opc/src/version.VERSION=${version}"
  local comps=("gateway" "tui" "worker" "node")
  
  for platform in "${!MAP[@]}"; do
    IFS='/' read -r goos goarch <<< "${MAP[$platform]}"
    local ext=""; [ "$goos" = "windows" ] && ext=".exe"
    local dir="${BIN_DIR}/${platform}"; mkdir -p "$dir"
    for c in "${comps[@]}"; do
      local src="./cmd/${c}/"; [ "$c" = "node" ] && src="./cmd/node/"
      [ ! -d "$src" ] && { warn "${c}: no src"; continue; }
      CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch" go build $ldflags -o "${dir}/computehub-${c}${ext}" "$src"
    done
  done
  
  mkdir -p "${DEPLOY_DIR}/archive"
  for platform in "${!MAP[@]}"; do
    IFS='/' read -r goos goarch <<< "${MAP[$platform]}"
    local ext=""; [ "$goos" = "windows" ] && ext=".exe"
    local suffix="${goos}-${goarch}${ext}"
    for c in "${comps[@]}"; do
      src="${BIN_DIR}/${platform}/computehub-${c}${ext}"
      [ -f "$src" ] || continue
      dst="${DEPLOY_DIR}/computehub-${c}-${suffix}"
      chmod +x "$src"; cp "$src" "$dst"
      ok "${dst}"
    done
  done
  echo "$version" > "${DEPLOY_DIR}/version.txt"
  ok "build v${version} done"
}

cmd_deploy() {
  local host=$1 pass=$2 component=$3 version=$4 ssh_port=$5 deploy_user=$6 gw=$7

  [[ "$gw" != http://* ]] && [[ "$gw" != https://* ]] && gw="http://${gw}"

  echo "  Deploy ${component} to ${deploy_user}@${host}:${ssh_port} (v${version})"
  echo "  Gateway: ${gw}"

  # Connectivity
  ping -c 1 -W 2 "$host" >/dev/null 2>&1 || {
    nc -z -w 3 "$host" "$ssh_port" 2>/dev/null || { err "${host}:${ssh_port} unreachable"; exit 1; }
  }

  # SSH + platform
  ssh_exec "$host" "$pass" "$ssh_port" "$deploy_user" "uname -a" >/dev/null 2>&1 || { err "SSH failed"; exit 1; }
  local os_info=$(ssh_exec "$host" "$pass" "$ssh_port" "$deploy_user" "uname -s" 2>/dev/null)
  local arch_info=$(ssh_exec "$host" "$pass" "$ssh_port" "$deploy_user" "uname -m" 2>/dev/null)
  ok "${deploy_user}@${host} (${os_info} ${arch_info})"

  local platform="linux-amd64"
  case "${os_info},${arch_info}" in
    Linux,aarch64|Linux,arm64) platform="linux-arm64" ;;
    Linux,x86_64|Linux,amd64)  platform="linux-amd64" ;;
  esac

  # Parse component list
  local comps=()
  if [ "$component" = "all" ]; then comps=("gateway" "tui" "worker" "node")
  else IFS=',' read -ra comps <<< "$component"; fi

  # Transfer via Gateway download
  for c in "${comps[@]}"; do
    download_via_gateway "$host" "$pass" "$ssh_port" "$deploy_user" "$c" "$platform" "$gw"
  done

  # Push config.json template (remote auto-generate)
  echo "  Push config.json template..."
  local config_content=$(cat "${PROJECT_DIR}/config.template.json")
  ssh_exec "$host" "$pass" "$ssh_port" "$deploy_user" "
    cat > ~/config.json << 'CONFIGEOF'
${config_content}
CONFIGEOF
    echo \"✅ config.json written\"
  "

  # Install & start
  local cmd="set -e; mkdir -p /tmp;"
  cmd+='if [ -d /data/data/com.termux/files/usr/bin ]; then B=/data/data/com.termux/files/usr/bin; else B=/usr/local/bin; fi;'
  for c in "${comps[@]}"; do
    local ext=""; [[ "$platform" == windows-* ]] && ext=".exe"
    cmd+="chmod +x ~/computehub-${c}${ext} 2>/dev/null;"
    cmd+="mkdir -p \$B 2>/dev/null; cp ~/computehub-${c}${ext} \$B/computehub-${c} 2>/dev/null;"
  done

  # Start gateway
  local has_gw=false
  for c in "${comps[@]}"; do [ "$c" = "gateway" ] && has_gw=true; done
  if $has_gw; then
    cmd+="pkill -f computehub-gateway 2>/dev/null || true;"
    cmd+="G=\$(command -v computehub-gateway || echo ~/computehub-gateway);"
    cmd+="nohup \$G > /tmp/gateway.log 2>&1 & sleep 2;"
  fi

  # Start worker
  local has_wk=false
  for c in "${comps[@]}"; do [ "$c" = "worker" ] && has_wk=true; done
  if $has_wk; then
    local node_id="${NODE_ID:-cqf-${host##*.}}"
    local region="${REGION:-cn-east}"
    cmd+="pkill -f computehub-worker 2>/dev/null || true;"
    cmd+="W=\$(command -v computehub-worker || echo ~/computehub-worker);"
    cmd+="nohup \$W --gw ${gw} --node-id ${node_id} --region ${region} > /tmp/worker.log 2>&1 &"
  fi

  ssh_exec "$host" "$pass" "$ssh_port" "$deploy_user" "$cmd" 2>&1 | tail -5 || true

  # Verify
  if $has_gw; then
    curl -s --connect-timeout 5 "${gw}/api/health" 2>/dev/null | grep -qi "healthy" && ok "Gateway" || warn "Gateway N/A"
  fi
  if $has_wk; then
    ssh_exec "$host" "$pass" "$ssh_port" "$deploy_user" "ps aux | grep computehub-worker | grep -v grep" \
      && ok "Worker running" || warn "Worker not detected"
  fi
  ok "Deploy done: ${comps[*]}"
}

# ============================================================
# Main
# ============================================================
CMD="${1:-help}"; [ $# -gt 0 ] && shift

case "$CMD" in
  build) cmd_build "${1:-$(get_version)}" ;;
  sync|sync-deploy) echo "use build instead";;
  deploy|all)
    MODE="$CMD"
    HOST=""; PASS=""; COMPONENT="all"; PORT="${SSH_PORT:-22}"
    GATEWAY="${GATEWAY_ADDR:-}"; VERSION=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --component) shift; COMPONENT="$1" ;;
        --port)      shift; PORT="$1" ;;
        --gateway)   shift; GATEWAY="$1" ;;
        --version)   shift; VERSION="$1" ;;
        --node-id)   shift; NODE_ID="$1" ;;
        --region)    shift; REGION="$1" ;;
        --user)      shift; DEPLOY_USER="$1" ;;
        *)
          [ -z "$HOST" ] && { HOST="$1"; shift; continue; }
          [ -z "$PASS" ] && { PASS="$1"; shift; continue; }
          shift
          ;;
      esac
      shift
    done
    [ -z "$HOST" ] && usage
    SSH_PORT="$PORT"; GATEWAY_ADDR="$GATEWAY"
    [ "$MODE" = "all" ] && cmd_build "${VERSION:-$(get_version)}"
    cmd_deploy "$HOST" "$PASS" "$COMPONENT" "${VERSION:-$(get_version)}" "$SSH_PORT" "${DEPLOY_USER:-root}" "${GATEWAY_ADDR:-${HOST}:8282}"
    ;;
  *) usage ;;
esac
