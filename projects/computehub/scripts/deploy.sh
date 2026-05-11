#!/bin/bash
# ============================================================
# ComputeHub 编译与部署标准流程
# 用法: bash scripts/deploy.sh <新版本号>
# 示例: bash scripts/deploy.sh 0.7.5
# ============================================================
set -euo pipefail

cd /root/.openclaw/workspace/projects/computehub

# --- 参数 ---
NEW_VERSION="${1:?用法: bash scripts/deploy.sh <版本号>}"
OLD_VERSION=$(cat deploy/version.txt 2>/dev/null || echo "none")
DEPLOY_DIR="deploy"
BUILD_DIR="build"
LDFLAGS="-s -w -X github.com/computehub/opc/src/version.VERSION=${NEW_VERSION}"

echo "========================================"
echo "  ComputeHub 编译与部署"
echo "  旧版本: ${OLD_VERSION}"
echo "  新版本: ${NEW_VERSION}"
echo "========================================"
echo ""

# --- Step 0: 环境检查 ---
echo "🔍 Step 0: 环境检查"
go version
echo ""

# --- Step 1: 编译 ---
echo "🔨 Step 1: 编译 ${NEW_VERSION}"
mkdir -p "${BUILD_DIR}"
rm -f "${BUILD_DIR}"/compute-worker-* "${BUILD_DIR}"/computehub-*

echo "  [1/6] Worker ARM64..."
CGO_ENABLED=0 GOARCH=arm64 go build ${LDFLAGS} \
  -o "${BUILD_DIR}/compute-worker-linux-arm64-${NEW_VERSION}" \
  ./cmd/worker/ 2>&1 && echo "    ✅"

echo "  [2/6] Worker AMD64..."
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build ${LDFLAGS} \
  -o "${BUILD_DIR}/compute-worker-linux-amd64-${NEW_VERSION}" \
  ./cmd/worker/ 2>&1 && echo "    ✅"

echo "  [3/6] Worker Win AMD64..."
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build ${LDFLAGS} \
  -o "${BUILD_DIR}/compute-worker-win-amd64.exe-${NEW_VERSION}" \
  ./cmd/worker/ 2>&1 && echo "    ✅"

echo "  [4/6] Worker Win ARM64..."
CGO_ENABLED=0 GOOS=windows GOARCH=arm64 go build ${LDFLAGS} \
  -o "${BUILD_DIR}/compute-worker-win-arm64.exe-${NEW_VERSION}" \
  ./cmd/worker/ 2>&1 && echo "    ✅"

echo "  [5/6] Gateway ARM64..."
CGO_ENABLED=0 go build ${LDFLAGS} \
  -o "${BUILD_DIR}/computehub-gateway-${NEW_VERSION}" \
  ./cmd/gateway/ 2>&1 && echo "    ✅"

echo "  [6/6] TUI ARM64..."
CGO_ENABLED=0 go build ${LDFLAGS} \
  -o "${BUILD_DIR}/computehub-tui-${NEW_VERSION}" \
  ./cmd/tui/ 2>&1 && echo "    ✅"
echo ""

# --- Step 2: 验证 ---
echo "🔍 Step 2: 验证编译产物"
ls -lh "${BUILD_DIR}"/compute-worker-linux-arm64-${NEW_VERSION}
file "${BUILD_DIR}"/compute-worker-linux-arm64-${NEW_VERSION}
echo ""

# --- Step 3: 部署 ---
echo "📦 Step 3: 部署到 ${DEPLOY_DIR}"

if [ "${OLD_VERSION}" != "${NEW_VERSION}" ] && [ "${OLD_VERSION}" != "none" ]; then
  echo "  归档旧版 ${OLD_VERSION}..."
  mkdir -p "${DEPLOY_DIR}/archive/${OLD_VERSION}"
  for f in compute-worker-linux-arm64 compute-worker-linux-amd64 \
           compute-worker-win-amd64.exe compute-worker-win-arm64.exe \
           computehub-gateway; do
    if [ -f "${DEPLOY_DIR}/${f}" ]; then
      cp "${DEPLOY_DIR}/${f}" "${DEPLOY_DIR}/archive/${OLD_VERSION}/"
      echo "    archived: ${f}"
    fi
  done
else
  echo "  首次部署，无需归档"
fi

# 复制新二进制（覆盖无后缀 — 升级链路硬编码）
cp "${BUILD_DIR}/compute-worker-linux-arm64-${NEW_VERSION}" "${DEPLOY_DIR}/compute-worker-linux-arm64"
cp "${BUILD_DIR}/compute-worker-linux-amd64-${NEW_VERSION}" "${DEPLOY_DIR}/compute-worker-linux-amd64"
cp "${BUILD_DIR}/compute-worker-win-amd64.exe-${NEW_VERSION}" "${DEPLOY_DIR}/compute-worker-win-amd64.exe"
cp "${BUILD_DIR}/compute-worker-win-arm64.exe-${NEW_VERSION}" "${DEPLOY_DIR}/compute-worker-win-arm64.exe"
cp "${BUILD_DIR}/computehub-gateway-${NEW_VERSION}" "${DEPLOY_DIR}/computehub-gateway"

chmod +x "${DEPLOY_DIR}/compute-worker-linux-arm64" \
         "${DEPLOY_DIR}/compute-worker-linux-amd64" \
         "${DEPLOY_DIR}/computehub-gateway"
echo "  ✅ 二进制已部署"
echo ""

# --- Step 4: 更新版本号 ---
echo "🔖 Step 4: 更新版本号为 ${NEW_VERSION}"
echo "${NEW_VERSION}" > "${DEPLOY_DIR}/version.txt"
echo "  $(cat ${DEPLOY_DIR}/version.txt)"
echo ""

# --- Step 5: 生成校验和 ---
echo "🔐 Step 5: 生成 SHA256"
cd "${DEPLOY_DIR}"
sha256sum compute-worker-linux-arm64 \
    compute-worker-linux-amd64 \
    compute-worker-win-amd64.exe \
    compute-worker-win-arm64.exe \
    computehub-gateway > sha256-current.txt
cat sha256-current.txt
cd ..
echo ""

# --- Step 6: 更新 VERSIONS.md ---
echo "📝 Step 6: 更新 VERSIONS.md"
cd "${DEPLOY_DIR}"
ARM_SHA=$(sha256sum compute-worker-linux-arm64 | awk '{print $1}')
AMD_SHA=$(sha256sum compute-worker-linux-amd64 | awk '{print $1}')
cat >> VERSIONS.md << EOF

## ${NEW_VERSION} ($(date +%Y-%m-%d))
- SHA256 (arm64): ${ARM_SHA}
- SHA256 (amd64): ${AMD_SHA}
EOF
cd ..
echo "  ✅ VERSIONS.md updated"
echo ""

# --- Step 7: 清理旧归档 ---
echo "🧹 Step 7: 清理旧归档"
ARCHIVE_COUNT=$(ls -1 "${DEPLOY_DIR}/archive/" 2>/dev/null | wc -l)
if [ "${ARCHIVE_COUNT}" -gt 3 ]; then
  REMOVE=$(ls -1 "${DEPLOY_DIR}/archive/" | sort -V | head -1)
  echo "  清理: ${REMOVE}"
  rm -rf "${DEPLOY_DIR}/archive/${REMOVE}"
else
  echo "  归档版本: ${ARCHIVE_COUNT}/3"
fi
echo ""

# --- Step 8: 完成 ---
echo "========================================"
echo "  ✅ 部署完成!"
echo "  版本: ${NEW_VERSION}"
echo "  文件: deploy/compute-worker-linux-arm64"
echo "========================================"
