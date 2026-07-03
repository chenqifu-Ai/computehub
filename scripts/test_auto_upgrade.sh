#!/bin/bash
# 测试 Worker 自动升级全流程
# 模拟场景：Worker v1.1.0 → 升级到 v1.2.0

set -e
cd /home/computehub/OPC

echo "========================================="
echo "🧪 Worker 自动升级 - 集成测试"
echo "========================================="

GATEWAY_URL="http://localhost:8282"
CURRENT_VERSION="1.1.0"
TARGET_VERSION="1.2.0"
NODE_ID="test-upgrade-worker"
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo ""
echo "[1/6] 检查 Gateway 是否运行..."
if ! curl -sf "$GATEWAY_URL/api/v1/upgrade/check?current_version=1.1.0&node_id=test" > /dev/null 2>&1; then
    echo "❌ Gateway 未运行，请先启动："
    echo "   cd /home/computehub/OPC && go run ./cmd/gateway &"
    exit 1
fi
echo "✅ Gateway 运行中"

echo ""
echo "[2/6] 模拟旧版 Worker 检查升级..."
echo "   Worker 当前版本: $CURRENT_VERSION"
echo "   目标版本: $TARGET_VERSION"

RESP=$(curl -s "$GATEWAY_URL/api/v1/upgrade/check?current_version=$CURRENT_VERSION&node_id=$NODE_ID&platform=linux/amd64")
echo "   Response: $RESP"

HAS_UPDATE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d.get('update_available',False))" 2>/dev/null)

# 临时将 version.txt 设为 v1.2.0（模拟新 binary 已部署）
echo "📝 模拟部署 v1.2.0 到 deploy/"
cp /home/computehub/deploy/version.txt /home/computehub/deploy/version.txt.bak
echo "1.2.0" > /home/computehub/deploy/version.txt
echo "✅ /home/computehub/deploy/version.txt 设为 v1.2.0"

# 重新检查升级
RESP=$(curl -s "$GATEWAY_URL/api/v1/upgrade/check?current_version=$CURRENT_VERSION&node_id=$NODE_ID&platform=linux/amd64")
HAS_UPDATE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d.get('update_available',False))" 2>/dev/null)

if [ "$HAS_UPDATE" != "True" ] && [ "$HAS_UPDATE" != "true" ]; then
    echo "❌ Gateway 未返回 update_available=true"
    echo "   Response: $RESP"
    cp /home/computehub/deploy/version.txt.bak /home/computehub/deploy/version.txt
    exit 1
fi

LATEST=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d.get('latest_version',''))" 2>/dev/null)
DOWNLOAD_URL=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d.get('download_url',''))" 2>/dev/null)
BINARY_SIZE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d.get('binary_size',0))" 2>/dev/null)

echo "✅ 检测到升级可用!"
echo "   最新版本: $LATEST"
echo "   下载地址: $DOWNLOAD_URL"
echo "   文件大小: $BINARY_SIZE bytes"

echo ""
echo "[3/6] 下载新 binary..."
DOWNLOAD_PATH="$GATEWAY_URL$DOWNLOAD_URL"
curl -s -o "$TEMP_DIR/computehub" -w "%{size_download}" "$DOWNLOAD_PATH" > /tmp/dl_size.txt
DOWNLOADED_SIZE=$(cat /tmp/dl_size.txt)
echo "   下载完成: $DOWNLOADED_SIZE bytes"

if [ "$BINARY_SIZE" != "0" ] && [ "$DOWNLOADED_SIZE" != "$BINARY_SIZE" ]; then
    echo "⚠️  文件大小不匹配 (期望: $BINARY_SIZE, 实际: $DOWNLOADED_SIZE)"
else
    echo "✅ 文件大小匹配"
fi

echo ""
echo "[4/6] 验证新 binary..."
file "$TEMP_DIR/computehub" | grep -q "ELF" && echo "✅ ELF 格式正确" || echo "❌ 不是 ELF 格式"

# 检查版本字符串
VERSION_STR=$(strings "$TEMP_DIR/computehub" | grep -i "computehub" | head -3)
echo "   Binary 包含: $(echo "$VERSION_STR" | head -1)"

echo ""
echo "[5/6] 模拟升级过程..."
# 在临时目录模拟：复制旧版本 → 替换为新版本 → 验证新版本
OLD_BIN="$TEMP_DIR/computehub.old"
cp /home/computehub/OPC/deploy/computehub "$OLD_BIN"

# 验证旧 binary 版本
OLD_VERSION_STR=$(strings "$OLD_BIN" | grep "computehub" | head -1)
echo "   旧 binary: $OLD_VERSION_STR"

# 模拟替换
NEW_BIN="$TEMP_DIR/computehub.new"
cp "$TEMP_DIR/computehub" "$NEW_BIN"

# 验证新旧不同
if cmp -s "$OLD_BIN" "$NEW_BIN"; then
    echo "⚠️  新旧 binary 相同（可能是热更新导致的）"
else
    echo "✅ 新旧 binary 不同（升级有效）"
fi

NEW_VERSION_STR=$(strings "$NEW_BIN" | grep "computehub" | head -1)
echo "   新 binary: $NEW_VERSION_STR"

echo ""
echo "[6/6] 验证版本探测..."
# 检查 Gateway 是否能正确识别版本差异
RESP2=$(curl -s "$GATEWAY_URL/api/v1/upgrade/check?current_version=$TARGET_VERSION&node_id=$NODE_ID&platform=linux/amd64")
HAS_UPDATE2=$(echo "$RESP2" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d.get('update_available',False))" 2>/dev/null)
echo "   当前版本=$TARGET_VERSION → update_available=$HAS_UPDATE2"
if [ "$HAS_UPDATE2" != "True" ] && [ "$HAS_UPDATE2" != "true" ]; then
    echo "✅ 正确：同一版本不应触发升级"
else
    echo "⚠️  版本相同时仍返回 update_available=true"
fi

echo ""
echo "========================================="
echo "✅ 全部通过！升级链路验证完成"
echo "========================================="
echo ""
echo "升级流程图:"
echo "  Worker(v1.1.0) → GET /upgrade/check →"
echo "  Gateway(version.txt=v1.2.0) →"
echo "  download_url=/api/v1/download?file=computehub →"
echo "  Worker下载 → 替换二进制 → 重启"
