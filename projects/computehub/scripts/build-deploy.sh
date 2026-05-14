#!/bin/bash
# ComputeHub deploy build — 编译单一二进制到 deploy 目录
# 输出: deploy/{version}/{platform}/computehub{,.exe}
#        deploy/computehub (当前平台)

set -eu
cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)

VERSION=$(grep 'var VERSION' src/version/version.go | awk -F'"' '{print $2}')
PLATFORMS=("linux-amd64" "linux-arm64" "darwin-amd64" "darwin-arm64" "windows-amd64")
DEPLOY_DIR="${PROJECT_DIR}/deploy"

echo "=== ComputeHub $VERSION deploy build ==="

mkdir -p "$DEPLOY_DIR"

for PLATFORM in "${PLATFORMS[@]}"; do
  os=$(echo "$PLATFORM" | cut -d- -f1)
  arch=$(echo "$PLATFORM" | cut -d- -f2)
  ext=""; [ "$os" = "windows" ] && ext=".exe"

  mkdir -p "${DEPLOY_DIR}/${PLATFORM}"

  printf "  ${PLATFORM} ... "
  CGO_ENABLED=0 GOOS=$os GOARCH=$arch \
    go build -ldflags="-s -w" \
    -o "${DEPLOY_DIR}/${PLATFORM}/computehub${ext}" "./cmd/computehub/" 2>&1

  chmod +x "${DEPLOY_DIR}/${PLATFORM}/computehub${ext}" 2>/dev/null || true
  size=$(stat -c%s "${DEPLOY_DIR}/${PLATFORM}/computehub${ext}" 2>/dev/null || echo "0")
  echo "OK ($(awk "BEGIN{printf \"%.1f\", $size/1024/1024}") MB)"
done

# 同时将当前平台的 copy 到根目录
CURRENT_OS=$(uname -s | tr '[:upper:]' '[:lower:]')
CURRENT_ARCH=$(uname -m)
case "$CURRENT_ARCH" in
  aarch64|arm64)  CURRENT_ARCH="arm64" ;;
  x86_64|amd64)   CURRENT_ARCH="amd64" ;;
esac
CURRENT_PLAT="${CURRENT_OS}-${CURRENT_ARCH}"

if [ -f "${DEPLOY_DIR}/${CURRENT_PLAT}/computehub" ]; then
  cp "${DEPLOY_DIR}/${CURRENT_PLAT}/computehub" "${DEPLOY_DIR}/computehub"
  echo ""
  echo "📌 当前平台 ${CURRENT_PLAT}: deploy/computehub"
fi

# 版本目录
for PLATFORM in "${PLATFORMS[@]}"; do
  mkdir -p "${DEPLOY_DIR}/${VERSION}/${PLATFORM}"
  ext=""; [[ "$PLATFORM" == windows-* ]] && ext=".exe"
  if [ -f "${DEPLOY_DIR}/${PLATFORM}/computehub${ext}" ]; then
    cp "${DEPLOY_DIR}/${PLATFORM}/computehub${ext}" "${DEPLOY_DIR}/${VERSION}/${PLATFORM}/computehub${ext}"
  fi
done

echo ""
echo "--- sha256sums ---"
find "${DEPLOY_DIR}/${VERSION}" -type f -name "computehub*" | sort | xargs sha256sum > "${DEPLOY_DIR}/sha256sums-${VERSION}.txt"
echo "  deploy/sha256sums-${VERSION}.txt"

echo "$VERSION" > "${DEPLOY_DIR}/version.txt"
echo "  deploy/version.txt -> $VERSION"

echo ""
echo "=== DONE: v$VERSION ==="
echo "文件:"
find "${DEPLOY_DIR}" -maxdepth 2 -type f -name "computehub*" | sort | while read f; do
  echo "  $(ls -lh "$f" | awk '{print $5}') $f"
done
