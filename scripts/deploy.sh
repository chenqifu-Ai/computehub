#!/bin/bash
# deploy.sh — ComputeHub 一键编译部署脚本
# 用法:
#   bash scripts/deploy.sh                 # 完整部署（编译+同步+重启+验证）
#   bash scripts/deploy.sh build           # 仅编译
#   bash scripts/deploy.sh sync            # 仅同步 deploy/
#   bash scripts/deploy.sh gateway-restart # 仅重启 Gateway
#   bash scripts/deploy.sh verify          # 仅验证
#   bash scripts/deploy.sh --all           # 等同无参数

set -euo pipefail

cd "$(dirname "$0")/.."

VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')
if [ -z "$VERSION" ]; then
    VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
fi

echo "================================================"
echo "  📦 ComputeHub v${VERSION} 一键部署"
echo "================================================"
echo ""

# ── Step 1/4: 编译 ──
do_build() {
    echo "🔨 Step 1/4: 编译 ${VERSION}"
    echo "──────────────────────────────────────────────"
    bash scripts/build_all.sh
    echo ""
    echo "🔍 验证编译产物..."
    local fail=0
    for plat in linux-amd64 linux-arm64 darwin-amd64 darwin-arm64 windows-amd64; do
        local ext=""; [ "$plat" = "windows-amd64" ] && ext=".exe"
        local bin="bin/${plat}/computehub${ext}"
        if [ -f "$bin" ]; then
            echo "  ✅ ${plat}: $(stat -c%s "$bin" 2>/dev/null || stat -f%z "$bin") bytes"
        else
            echo "  ❌ ${plat}: 文件不存在 ($bin)"
            fail=1
        fi
    done
    [ "$fail" -eq 0 ] && echo "  ✅ 编译验证通过" || { echo "  ❌ 编译验证失败"; exit 1; }
    echo ""
}

# ── Step 2/4: 同步 deploy/ ──
do_sync() {
    echo "📂 Step 2/4: 同步到 deploy/"
    echo "──────────────────────────────────────────────"
    bash scripts/sync-deploy.sh
    echo ""
}

# ── Step 3/4: 更新 Gateway binary + 重启 ──
do_gateway_restart() {
    echo "🔄 Step 3/4: 更新 Gateway 并重启"
    echo "──────────────────────────────────────────────"

    if [ -f "bin/linux-amd64/computehub" ]; then
        echo "  🛑 停止 Gateway..."
        sudo systemctl stop computehub-gateway
        sleep 2

        echo "  📦 复制 binary 到 /usr/local/bin/computehub..."
        cp bin/linux-amd64/computehub /usr/local/bin/computehub
        chmod +x /usr/local/bin/computehub
        /usr/local/bin/computehub version

        echo "  🚀 启动 Gateway..."
        sudo systemctl start computehub-gateway
        sleep 3
    else
        echo "  ⚠️  没有找到 linux-amd64 编译产物"
    fi

    echo "  ✅ Gateway 状态:"
    sudo systemctl status computehub-gateway --no-pager -l 2>/dev/null | head -6 || true
    echo ""
}

# ── Step 4/4: 验证 ──
do_verify() {
    echo "✅ Step 4/4: 验证"
    echo "──────────────────────────────────────────────"

    local fail=0

    # 4a. Gateway 健康检查
    echo "  [1/6] Gateway 健康检查..."
    if curl -sf http://localhost:8282/api/health >/dev/null 2>&1; then
        echo "    ✅ Gateway 运行中"
    else
        echo "    ❌ Gateway 无响应"
        fail=1
    fi

    # 4b. 下载链路验证
    echo "  [2/6] 下载链路验证..."
    local tmp="/tmp/computehub-deploy-check-$$"
    local dl_fail=0
    for plat in "linux/arm64:computehub:arm64" "windows/amd64:computehub.exe:win64" "linux/amd64:computehub:amd64"; do
        IFS=':' read -r platform fname expected <<< "$plat"
        # platform 含 "/" (如 linux/arm64)，curl -o 会当目录，需转义
        local safe_platform="${platform//\//_}"
        local dl_status=0
        curl -s --max-time 30 "http://localhost:8282/api/v1/download?file=${fname}&platform=${platform}" -o "${tmp}-${safe_platform}" >/dev/null 2>&1 || dl_status=$?
        if [ "$dl_status" -eq 0 ]; then
            local fsize
            fsize=$(stat -c%s "${tmp}-${safe_platform}" 2>/dev/null) || fsize='?'
            echo "    ✅ ${platform}: ${expected} (${fsize} bytes)"
        else
            echo "    ⚠️  ${platform}: 下载失败 (exit=$dl_status)"
            echo "          (提示: 先跑 'bash scripts/deploy.sh sync' 生成 deploy/{platform}/)"
            dl_fail=1
        fi
    done
    rm -f ${tmp}-* 2>/dev/null || true

    # 4c. 升级检查验证
    echo "  [3/6] 升级检查验证..."
    local avail=$(curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=1.3.25\&platform=linux/arm64\&node_id=worker-arm" 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['update_available'])" 2>/dev/null)
    if [ "$avail" = "True" ]; then
        echo "    ✅ 升级检测正常 (update_available=True)"
    else
        echo "    ⚠️  升级检测异常 (update_available=${avail:-N/A})"
    fi

    # 4d. 集群状态
    echo "  [4/6] 集群节点状态..."
    curl -s http://localhost:8282/api/v2/nodes 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
for n in d['nodes']:
    ver = n.get('version','?')
    print(f'    🟢 {n[\"id\"]:20s} v{ver:10s} {n[\"status\"]}')
print(f'    总计: {d[\"online_nodes\"]} 在线 / {d[\"total_nodes\"]} 节点')
" 2>/dev/null || echo "    ⚠️  无法获取集群状态"

    # 4e. 二进制架构验证
    echo "  [5/6] 二进制架构验证..."
    for plat in "linux-amd64:x86-64" "linux-arm64:ARM aarch64" "windows-amd64:PE32+"; do
        IFS=':' read -r dir expected <<< "$plat"
        local bin="deploy/${dir}/computehub"
        [ "$dir" = "windows-amd64" ] && bin="deploy/${dir}/computehub.exe"
        if [ -f "$bin" ]; then
            local actual=$(file "$bin" 2>/dev/null)
            if echo "$actual" | grep -q "$expected"; then
                echo "    ✅ ${dir}: ${expected} ✅"
            else
                echo "    ❌ ${dir}: 期望 ${expected}, 实际 ${actual}"
                fail=1
            fi
        fi
    done

    # 4f. SHA256 一致性
    echo "  [6/6] SHA256 一致性检查..."
    local sha_file="deploy/sha256sums.txt"
    if [ -f "$sha_file" ]; then
        local ok=0; total=0
        while IFS= read -r line; do
            total=$((total+1))
            local hash=$(echo "$line" | awk '{print $1}')
            local file=$(echo "$line" | awk '{print $2}')
            local check_file="$file"
            [[ "$check_file" != deploy/* ]] && check_file="deploy/$check_file"
            local actual=$(sha256sum "$check_file" 2>/dev/null | awk '{print $1}')
            if [ "$hash" = "$actual" ]; then
                :
            else
                echo "    ❌ ${file}: SHA256 不匹配"
                ok=1
            fi
        done < "$sha_file"
        [ "$ok" -eq 0 ] && echo "    ✅ 所有 SHA256 校验一致 (${total} 个文件)" || fail=1
    else
        echo "    ⚠️  没有 sha256sums.txt"
    fi

    echo ""
    if [ "$fail" -eq 0 ]; then
        echo "🎉 部署完成! v${VERSION}"
    else
        echo "⚠️  部分验证失败，请检查上述输出"
        exit 1
    fi
}

# ── 主流程 ──
CASE="${1:-all}"

case "$CASE" in
    build)
        do_build
        ;;
    sync)
        do_sync
        ;;
    gateway-restart)
        do_gateway_restart
        ;;
    verify)
        do_verify
        ;;
    all|--all|"")
        do_build
        do_sync
        do_gateway_restart
        do_verify
        ;;
    *)
        echo "用法: bash scripts/deploy.sh [build|sync|gateway-restart|verify|all]"
        exit 1
        ;;
esac
