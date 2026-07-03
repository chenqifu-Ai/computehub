#!/bin/bash
# Windows Worker 自动升级标准测试
# 遵循 OPC-WIN-STD-001 标准流程
# 
# 测试目标：验证 Gateway 升级检查 + 二进制下载 + 版本管理链路
# 注意：这是服务端端点验证，不涉及实际推送给 Windows 节点
#
# 用法: bash scripts/test_win_upgrade.sh

set -e
cd /home/computehub/OPC

GATEWAY="http://localhost:8282"
TEMP_VER_FILE="/tmp/version_backup.txt"
BACKUP_VER=""
TEST_RESULT=0

echo "================================================"
echo "🧪 Windows Worker 自动升级标准测试"
echo "================================================"
echo ""

# ─── 辅助函数 ───
check_pass() { echo "  ✅ $1"; }
check_fail() { echo "  ❌ $1"; TEST_RESULT=1; }
check_warn() { echo "  ⚠️  $1"; }

# ─── 1. 前置检查 ───
echo "[1/7] 前置检查"
echo "  节点列表:"
curl -s "$GATEWAY/api/v1/nodes/list" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for n in data.get('data', []):
    status = n.get('status', '?')
    ver = n.get('version', '?')
    node_id = n.get('node_id', '?')
    print(f'    {node_id:25s}  v{ver:8s}  [{status}]')
"
echo ""

# 确认 windows-mobile 在线
WINDOWS_EXISTS=$(curl -s "$GATEWAY/api/v1/nodes/list" | python3 -c "
import sys, json
for n in json.load(sys.stdin).get('data', []):
    if n['node_id'] == 'windows-mobile':
        print('online' if n['status'] == 'online' else 'offline')
        sys.exit(0)
print('not_found')
")
if [ "$WINDOWS_EXISTS" = "online" ]; then
    check_pass "windows-mobile 节点在线"
elif [ "$WINDOWS_EXISTS" = "offline" ]; then
    check_warn "windows-mobile 节点离线（升级测试仍可验证端点）"
else
    check_fail "windows-mobile 节点不存在"
fi

# ─── 2. 检查 deploy 目录完整性 ───
echo ""
echo "[2/7] 检查 deploy 目录完整性"

VER_TXT=$(cat /home/computehub/deploy/version.txt 2>/dev/null)
if [ -z "$VER_TXT" ]; then
    check_fail "deploy/version.txt 不存在"
else
    check_pass "deploy/version.txt = $VER_TXT"
fi

# 检查 Windows 二进制
WIN_BIN="/home/computehub/deploy/windows-amd64/computehub.exe"
if [ -f "$WIN_BIN" ]; then
    WIN_SIZE=$(stat -c%s "$WIN_BIN" 2>/dev/null || stat -f%z "$WIN_BIN" 2>/dev/null)
    check_pass "deploy/windows-amd64/computehub.exe 存在 (${WIN_SIZE} bytes)"
else
    check_fail "deploy/windows-amd64/computehub.exe 不存在"
fi

# 检查 flat binary
FLAT_WIN="/home/computehub/deploy/computehub.exe"
if [ -f "$FLAT_WIN" ]; then
    check_pass "deploy/computehub.exe (flat) 存在"
else
    check_warn "deploy/computehub.exe (flat) 不存在（upgrade 可能找不到）"
fi

# ─── 3. 测试升级检查端点 ───
echo ""
echo "[3/7] 测试升级检查端点"

# 场景 A: 版本号与 Gateway 一致 → 不应更新
RESP_A=$(curl -s "$GATEWAY/api/v1/upgrade/check?current_version=1.2.0&node_id=windows-mobile&platform=windows/amd64")
UPDATE_A=$(echo "$RESP_A" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['update_available'])")
if [ "$UPDATE_A" = "False" ]; then
    check_pass "场景A: 版本一致 → update_available=false ✅"
else
    check_fail "场景A: 版本一致却返回 update_available=true ❌"
fi

# 场景 B: 版本号与 Gateway 不一致 → 应该更新
RESP_B=$(curl -s "$GATEWAY/api/v1/upgrade/check?current_version=1.1.0&node_id=windows-mobile&platform=windows/amd64")
UPDATE_B=$(echo "$RESP_B" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d['update_available']); print(d['latest_version']); print(d['download_url']); print(d['binary_size'])")
echo "$UPDATE_B" > /tmp/upgrade_check_result.txt
HAS_UPDATE_B=$(head -1 /tmp/upgrade_check_result.txt)
LATEST=$(sed -n '2p' /tmp/upgrade_check_result.txt)
DOWNLOAD_URL=$(sed -n '3p' /tmp/upgrade_check_result.txt)
BINARY_SIZE=$(sed -n '4p' /tmp/upgrade_check_result.txt)

if [ "$HAS_UPDATE_B" = "True" ]; then
    check_pass "场景B: 版本不一致 → update_available=true ✅"
    check_pass "  最新版本: $LATEST"
    check_pass "  下载URL: $DOWNLOAD_URL"
    check_pass "  文件大小: $BINARY_SIZE bytes"
else
    check_fail "场景B: 版本不一致却返回 update_available=false ❌"
fi

# ─── 4. 测试下载端点 ───
echo ""
echo "[4/7] 测试下载端点"

# 场景 C: 下载 computehub.exe (flat)
HTTP_CODE_C=$(curl -s -o /tmp/test_dl_c.exe -w "%{http_code}" "$GATEWAY/api/v1/download?file=computehub.exe")
DL_SIZE_C=$(stat -c%s /tmp/test_dl_c.exe 2>/dev/null || stat -f%z /tmp/test_dl_c.exe 2>/dev/null)
if [ "$HTTP_CODE_C" = "200" ]; then
    check_pass "下载 computehub.exe: HTTP 200, ${DL_SIZE_C} bytes ✅"
else
    check_fail "下载 computehub.exe: HTTP $HTTP_CODE_C ❌"
fi

# 场景 D: 下载 computehub (Linux, 用于对比)
HTTP_CODE_D=$(curl -s -o /tmp/test_dl_d.bin -w "%{http_code}" "$GATEWAY/api/v1/download?file=computehub")
DL_SIZE_D=$(stat -c%s /tmp/test_dl_d.bin 2>/dev/null || stat -f%z /tmp/test_dl_d.bin 2>/dev/null)
if [ "$HTTP_CODE_D" = "200" ]; then
    check_pass "下载 computehub (Linux): HTTP 200, ${DL_SIZE_D} bytes ✅"
else
    check_fail "下载 computehub (Linux): HTTP $HTTP_CODE_D ❌"
fi

# 验证 Windows 和 Linux 二进制不同
if [ "$DL_SIZE_C" != "$DL_SIZE_D" ]; then
    check_pass "Windows (${DL_SIZE_C}B) ≠ Linux (${DL_SIZE_D}B) ✅"
else
    check_warn "Windows 和 Linux 二进制大小相同（可能交叉了）"
fi

# 验证下载的是真实文件
FILE_TYPE=$(file /tmp/test_dl_c.exe 2>/dev/null | head -1)
if echo "$FILE_TYPE" | grep -qi "PE\|windows\|executable"; then
    check_pass "Windows binary 格式正确: $FILE_TYPE"
else
    check_fail "Windows binary 格式异常: $FILE_TYPE"
fi

FILE_TYPE_L=$(file /tmp/test_dl_d.bin 2>/dev/null | head -1)
if echo "$FILE_TYPE_L" | grep -qi "ELF\|executable"; then
    check_pass "Linux binary 格式正确: $FILE_TYPE_L"
else
    check_fail "Linux binary 格式异常: $FILE_TYPE_L"
fi

# ─── 5. 验证版本管理一致性 ───
echo ""
echo "[5/7] 验证版本管理一致性"

# 检查 Gateway 返回的 binary_size 和实际下载大小是否一致
EXPECTED_SIZE=$(sed -n '4p' /tmp/upgrade_check_result.txt)
if [ "$EXPECTED_SIZE" = "$DL_SIZE_C" ]; then
    check_pass "版本探测 binary_size ($EXPECTED_SIZE) = 实际下载大小 ($DL_SIZE_C) ✅"
else
    check_warn "binary_size ($EXPECTED_SIZE) ≠ 实际下载 ($DL_SIZE_C)"
fi

# ─── 6. 测试 Gallery 上传端点 ───
echo ""
echo "[6/7] 测试 Gallery 文件上传/下载一致性"

# Gallery 文件应该和 deploy 目录的 binary 一致
GALLERY_MD5=$(curl -s "$GATEWAY/api/v1/files/computehub-windows-amd64.exe" -o /tmp/gallery_dl.exe -w "" 2>/dev/null)
if [ -f /tmp/gallery_dl.exe ]; then
    GALLERY_SIZE=$(stat -c%s /tmp/gallery_dl.exe 2>/dev/null || stat -f%z /tmp/gallery_dl.exe 2>/dev/null)
    check_pass "Gallery 文件存在: ${GALLERY_SIZE} bytes"
    
    # Gallery 和 deploy 应该一致
    DEPLOY_MD5=$(md5sum deploy/windows-amd64/computehub.exe 2>/dev/null | cut -d' ' -f1)
    GALLERY_MD5_VAL=$(md5sum /tmp/gallery_dl.exe 2>/dev/null | cut -d' ' -f1)
    if [ "$DEPLOY_MD5" = "$GALLERY_MD5_VAL" ]; then
        check_pass "Gallery 文件 = deploy 文件 (MD5: $DEPLOY_MD5)"
    else
        check_warn "Gallery ≠ deploy (可能 Gallery 是旧版本，这是正常的)"
    fi
else
    check_warn "Gallery 文件中 computehub-windows-amd64.exe 不存在（未上传过）"
fi

# ─── 7. 模拟升级流程（版本差异测试） ───
echo ""
echo "[7/7] 模拟升级场景"

# 保存当前版本
cp deploy/version.txt "$TEMP_VER_FILE"
BACKUP_VER=$(cat /home/computehub/deploy/version.txt)

# 临时设置为更高的版本号，模拟"有新版本部署了"
echo "1.2.1" > /home/computehub/deploy/version.txt

# 重新检查升级
RESP_SIM=$(curl -s "$GATEWAY/api/v1/upgrade/check?current_version=1.1.0&node_id=windows-mobile&platform=windows/amd64")
SIM_UPDATE=$(echo "$RESP_SIM" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['update_available'])")
SIM_LATEST=$(echo "$RESP_SIM" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['latest_version'])")

if [ "$SIM_UPDATE" = "True" ] && [ "$SIM_LATEST" = "1.2.1" ]; then
    check_pass "模拟场景: Worker=1.1.0 → Gateway=1.2.1, update_available=true ✅"
else
    check_fail "模拟场景失败: update=$SIM_UPDATE, latest=$SIM_LATEST"
fi

# 恢复版本
cp "$TEMP_VER_FILE" /home/computehub/deploy/version.txt
check_pass "恢复版本文件: $BACKUP_VER"

# 清理
rm -f /tmp/test_dl_c.exe /tmp/test_dl_d.bin /tmp/gallery_dl.exe /tmp/upgrade_check_result.txt "$TEMP_VER_FILE"

# ─── 总结 ───
echo ""
echo "================================================"
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ 全部通过！Windows 升级链路验证完成"
else
    echo "❌ 部分检查未通过，请查看上方标记"
fi
echo "================================================"
echo ""
echo "升级流程总结:"
echo "  1. Worker (旧版) → GET /api/v1/upgrade/check"
echo "  2. Gateway → 读 deploy/version.txt 对比"
echo "  3. 返回 download_url=/api/v1/download?file=computehub.exe"
echo "  4. Worker 下载 → 替换二进制 → 重启"
echo ""
echo "后续实际推送到 Windows 节点:"
echo "  bash scripts/test_auto_upgrade.sh --push-windows"
echo "  或通过 OPC 提交升级命令到 windows-mobile"

exit $TEST_RESULT
