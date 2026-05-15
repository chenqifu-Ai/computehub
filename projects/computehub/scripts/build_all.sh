#!/bin/bash
# ComputeHub 全平台编译脚本（三合一版本）
# 输出: bin/{platform}/computehub{,.exe}

set -e

cd "$(dirname "$0")/.."
VERSION=$(grep 'VERSION = "' src/version/version.go | awk -F'"' '{print $2}')
PLATFORMS=("linux-amd64" "linux-arm64" "darwin-amd64" "darwin-arm64" "windows-amd64")

echo "🔨 ComputeHub $VERSION 全平台编译（三合一）"
echo "================================="

mkdir -p bin

# 映射表
declare -A GOOS GOARCH EXT
GOOS["linux-amd64"]="linux";   GOARCH["linux-amd64"]="amd64"
GOOS["linux-arm64"]="linux";   GOARCH["linux-arm64"]="arm64"
GOOS["darwin-amd64"]="darwin"; GOARCH["darwin-amd64"]="amd64"
GOOS["darwin-arm64"]="darwin"; GOARCH["darwin-arm64"]="arm64"
GOOS["windows-amd64"]="windows"; GOARCH["windows-amd64"]="amd64"
EXT["windows-amd64"]=".exe"

TOTAL=${#PLATFORMS[@]}
PASS=0
FAIL=0

for PLATFORM in "${PLATFORMS[@]}"; do
    os=${GOOS[$PLATFORM]}
    arch=${GOARCH[$PLATFORM]}
    ext=${EXT[$PLATFORM]:-}
    out="bin/${PLATFORM}/computehub${ext}"
    tmp="${out}.tmp"

    echo "[$((PASS+FAIL+1))/$TOTAL] computehub → $PLATFORM"

    if CGO_ENABLED=0 GOOS=$os GOARCH=$arch \
        go build -ldflags="-X github.com/computehub/opc/src/version.VERSION=${VERSION}" \
        -o "$tmp" "./cmd/computehub/" 2>&1; then
        mkdir -p "$(dirname "$out")"
        mv "$tmp" "$out"
        chmod +x "$out"
        size=$(stat -c%s "$out" 2>/dev/null || stat -f%z "$out" 2>/dev/null)
        size_mb=$(awk "BEGIN{printf \"%.1f\", $size/1024/1024}")
        echo "   ✅ $out (${size_mb}MB)"
        PASS=$((PASS + 1))
    else
        rm -f "$tmp"
        echo "   ❌ 编译失败"
        FAIL=$((FAIL + 1))
    fi
done

echo "================================="
echo "结果: ${PASS}/${TOTAL} 通过, ${FAIL} 失败"

# 生成 sha256sums
echo ""
echo "📝 生成 sha256sums..."
cd bin
find . -type f \( -name "computehub" -o -name "computehub.exe" \) -not -name "*.tmp" | sort | xargs sha256sum > sha256sums-${VERSION}.txt
echo "   sha256sums-${VERSION}.txt"
cd ..

echo "✅ 编译完成!"
echo ""
echo "💡 提示：用 sync-deploy.sh 同步到 deploy/ 目录"
echo "   bash scripts/sync-deploy.sh"
