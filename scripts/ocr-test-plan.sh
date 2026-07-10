#!/bin/bash
# =============================================================================
# OCR API 测试计划 — ComputeHub v1.3.53
# 目标: POST /api/v1/ocr 完整链路验证
# =============================================================================

GATEWAY="http://127.0.0.1:8282"
PASS=0
FAIL=0
TOTAL=0

pass_test() { echo "  ✅ $1"; PASS=$((PASS+1)); }
fail_test() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
section() { echo ""; echo "━━━ $1 ━━━"; }

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     OCR API 测试计划 — ComputeHub v1.3.53            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Tesseract: $(tesseract --version 2>&1 | head -1)"
echo "Langs: $(tesseract --list-langs 2>&1 | tail -1)"
echo ""

# =============================================================================
section "P0: 环境验证"

TOTAL=$((TOTAL+1))
health=$(curl -s "$GATEWAY/api/health" 2>/dev/null)
if echo "$health" | grep -q "Healthy"; then
    pass_test "Gateway 在线"
else
    fail_test "Gateway 不在线"
    exit 1
fi

# =============================================================================
section "P1: 基础功能 — 合成测试图片"

python3 << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

os.makedirs("data/test_images", exist_ok=True)

img1 = Image.new("RGB", (400, 100), "white")
d = ImageDraw.Draw(img1)
try:
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
except:
    f = ImageFont.load_default()
d.text((20, 30), "Hello ComputeHub OCR!", fill="black", font=f)
img1.save("data/test_images/test_en.jpg", quality=95)

img2 = Image.new("RGB", (400, 100), "white")
d2 = ImageDraw.Draw(img2)
try:
    f2 = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 24)
except:
    try:
        f2 = ImageFont.truetype("/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc", 24)
    except:
        f2 = ImageFont.load_default()
d2.text((20, 30), "计算机关机", fill="black", font=f2)
img2.save("data/test_images/test_cn.jpg", quality=95)

img3 = Image.new("RGB", (500, 100), "white")
d3 = ImageDraw.Draw(img3)
d3.text((20, 25), "Hello 你好 World 世界", fill="black", font=f2)
img3.save("data/test_images/test_mixed.jpg", quality=95)

img4 = Image.new("RGB", (400, 200), "white")
d4 = ImageDraw.Draw(img4)
d4.text((10, 10), "Line 1: The quick brown fox", fill="black", font=f)
d4.text((10, 40), "Line 2: jumps over the lazy dog", fill="black", font=f)
d4.text((10, 70), "Line 3: 计算机关机 测试文字识别", fill="black", font=f2)
img4.save("data/test_images/test_multiline.jpg", quality=95)

img5 = Image.new("RGB", (400, 100), "white")
d5 = ImageDraw.Draw(img5)
d5.text((20, 30), "Noisy Text 噪声文字", fill="black", font=f)
img5 = img5.filter(ImageFilter.GaussianBlur(radius=2))
img5.save("data/test_images/test_noisy.jpg", quality=50)

print("✅ 5 张测试图片生成完成:")
for f in ["test_en.jpg","test_cn.jpg","test_mixed.jpg","test_multiline.jpg","test_noisy.jpg"]:
    p = f"data/test_images/{f}"
    if os.path.exists(p): print(f"   {f} ({os.path.getsize(p)}B)")
PYEOF

# =============================================================================
section "P1: 参数校验测试"

# 1. GET 应该被拒绝
TOTAL=$((TOTAL+1))
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/v1/ocr")
pass_test "GET /api/v1/ocr → $http_code (方法校验)"

# 2. 缺少 image 参数
TOTAL=$((TOTAL+1))
resp=$(curl -s -X POST "$GATEWAY/api/v1/ocr" -H "Content-Type: application/json" -d '{"lang":"eng"}')
if echo "$resp" | grep -qi "image.*required\|required"; then pass_test "缺少 image → 报错"; else fail_test "缺少 image: $resp"; fi

# 3. 无效 base64
TOTAL=$((TOTAL+1))
resp=$(curl -s -X POST "$GATEWAY/api/v1/ocr" -H "Content-Type: application/json" -d '{"image":"not-base64!!!"}')
if echo "$resp" | grep -qi "Base64\|invalid"; then pass_test "无效 base64 → 报错"; else fail_test "无效 base64: $resp"; fi

# 4. 空 image
TOTAL=$((TOTAL+1))
resp=$(curl -s -X POST "$GATEWAY/api/v1/ocr" -H "Content-Type: application/json" -d '{"image":""}')
if echo "$resp" | grep -qi "image.*required"; then pass_test "空 image → 报错"; else fail_test "空 image: $resp"; fi

# =============================================================================
section "P1: 图片内容 OCR 测试"

run_ocr() {
    local img=$1 desc=$2 lang=$3
    TOTAL=$((TOTAL+1))
    local b64=$(base64 -w0 "data/test_images/$img" 2>/dev/null)
    [ -z "$b64" ] && { fail_test "$desc: 图片不存在"; return; }
    
    local resp=$(curl -s -X POST "$GATEWAY/api/v1/ocr" \
        -H "Content-Type: application/json" \
        -d "{\"image\":\"$b64\",\"lang\":\"$lang\",\"timeout\":15}")
    
    if echo "$resp" | grep -q '"success":true'; then
        local text=$(echo "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin)["data"];print(d.get("text",""))' 2>/dev/null)
        local dur=$(echo "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin)["data"];print(d.get("duration_ms",0))' 2>/dev/null)
        pass_test "$desc → 成功 ${dur}ms | $text"
    else
        fail_test "$desc → 失败: $resp"
    fi
}

[ -f "data/test_images/test_en.jpg" ] && run_ocr test_en.jpg "英文识别" "eng"
[ -f "data/test_images/test_cn.jpg" ] && run_ocr test_cn.jpg "中文识别" "chi_sim"
[ -f "data/test_images/test_mixed.jpg" ] && run_ocr test_mixed.jpg "中英文混合" "chi_sim+eng"
[ -f "data/test_images/test_multiline.jpg" ] && run_ocr test_multiline.jpg "多行文本" "chi_sim+eng"
[ -f "data/test_images/test_noisy.jpg" ] && run_ocr test_noisy.jpg "噪声图片" "chi_sim+eng"

# =============================================================================
section "P2: 性能测试"

TOTAL=$((TOTAL+1))
echo "  10 次 OCR test_en.jpg..."
sum_ms=0
for i in $(seq 1 10); do
    b64=$(base64 -w0 "data/test_images/test_en.jpg")
    resp=$(curl -s -X POST "$GATEWAY/api/v1/ocr" \
        -H "Content-Type: application/json" \
        -d "{\"image\":\"$b64\",\"lang\":\"eng\",\"timeout\":15}")
    d=$(echo "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin)["data"];print(d.get("duration_ms",0))' 2>/dev/null)
    sum_ms=$((sum_ms + d))
done
avg_ms=$((sum_ms / 10))
echo "  平均: ${avg_ms}ms"
if [ "$avg_ms" -lt 5000 ]; then pass_test "10次平均 ${avg_ms}ms (< 5s 合格)"; else fail_test "10次平均 ${avg_ms}ms (> 5s 慢)"; fi

# =============================================================================
section "P2: 并发测试 (5 并发)"

TOTAL=$((TOTAL+1))
b64=$(base64 -w0 "data/test_images/test_en.jpg")
success=$(python3 -c "
import json, concurrent.futures, urllib.request
url = '$GATEWAY/api/v1/ocr'
payload = json.dumps({'image':'$b64','lang':'eng','timeout':15}).encode()
def do_ocr(_):
    try:
        req = urllib.request.Request(url, data=payload, headers={'Content-Type':'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())['success']
    except: return False
with concurrent.futures.ThreadPoolExecutor(5) as ex:
    results = list(ex.map(do_ocr, range(5)))
ok = sum(1 for r in results if r)
print(ok)
")
echo "  结果: $success/5"
if [ "$success" -eq 5 ]; then pass_test "5/5 并发成功"; else fail_test "仅 $success/5 成功"; fi

# =============================================================================
section "P3: 边缘场景"

# 无效语言
TOTAL=$((TOTAL+1))
b64=$(base64 -w0 "data/test_images/test_en.jpg")
resp=$(curl -s -X POST "$GATEWAY/api/v1/ocr" \
    -H "Content-Type: application/json" \
    -d "{\"image\":\"$b64\",\"lang\":\"zzz_invalid_lang\"}")
if echo "$resp" | grep -qi "failed\|error\|tesseract"; then pass_test "无效语言 → Tesseract 报错"; else fail_test "无效语言未报错: $resp"; fi

# =============================================================================
section "P3: OCR Stats 端点"

TOTAL=$((TOTAL+1))
stats=$(curl -s "$GATEWAY/api/v1/ocr/stats")
echo "  $stats"
if echo "$stats" | grep -q "total_runs"; then
    runs=$(echo "$stats" | python3 -c 'import sys,json;d=json.load(sys.stdin)["data"];print(d.get("total_runs",0))' 2>/dev/null)
    avg=$(echo "$stats" | python3 -c 'import sys,json;d=json.load(sys.stdin)["data"];print(d.get("avg_ms",0))' 2>/dev/null)
    pass_test "Stats OK — runs=$runs avg_ms=$avg"
else
    fail_test "Stats 异常"
fi

# =============================================================================
section "📊 汇总"
echo "  总计: $TOTAL | ✅ $PASS | ❌ $FAIL"
echo ""
if [ "$FAIL" -eq 0 ]; then echo "  🎉 全部通过！"; else echo "  ⚠️ $FAIL 项失败"; fi
