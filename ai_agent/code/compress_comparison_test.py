#!/usr/bin/env python3
"""压缩 vs 原图 AI 分析效果对比测试"""
import os, json, time, base64
from pathlib import Path

SRC_ORIG = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real5")
SRC_COMP = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real5_compressed")

test_photos = [
    ("IMG_20260430_174807.jpg", "夜景/暗光"),
    ("IMG_20260430_180223.jpg", "白天"),
    ("IMG_20260430_180637.jpg", "傍晚"),
]

prompt = """请非常详细地描述这张图片的内容。包括：
1. 场景类型和主要物体
2. 所有可见的文字信息
3. 数字、价格、时间等关键信息
4. 光线和天气
5. 任何值得注意的特征"""

API_URL = "http://58.23.129.98:8001/v1/chat/completions"
API_KEY = "Bearer sk-78sadn09bjawde123e"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": API_KEY
}

import requests

def analyze_image(img_path):
    """发送图片给 Qwen 多模态 API"""
    b64 = base64.b64encode(open(img_path, "rb").read()).decode()
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        "max_tokens": 4096,
        "temperature": 0.3
    }
    
    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=180)
    if r.status_code == 200:
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        reasoning = data.get("choices", [{}])[0].get("message", {}).get("reasoning", "")
        return content or reasoning
    else:
        return f"HTTP {r.status_code}: {r.text[:300]}"

print("="*80)
print("🔍 压缩 vs 原图 AI 分析效果对比测试")
print("="*80)

results = []

for i, (orig_name, desc) in enumerate(test_photos):
    orig_path = SRC_ORIG / orig_name
    comp_name = orig_name + "_1536q85.jpg"
    comp_path = SRC_COMP / comp_name
    
    if not orig_path.exists() or not comp_path.exists():
        print(f"\n⚠️ 跳过 {orig_name}")
        continue
    
    orig_size = os.path.getsize(orig_path)
    comp_size = os.path.getsize(comp_path)
    
    print(f"\n{'='*80}")
    print(f"📷 测试 {i+1}/{len(test_photos)}: {orig_name} ({desc})")
    print(f"   原图: {orig_size/1024/1024:.1f}MB")
    print(f"   压缩: {comp_size/1024:.1f}KB | 省 {(1-comp_size/orig_size)*100:.1f}%")
    print(f"{'─'*80}")
    
    # 分析原图
    print(f"\n⚪ 分析原图 {orig_size/1024/1024:.1f}MB...", end="", flush=True)
    t0 = time.time()
    try:
        orig_result = analyze_image(orig_path)
    except Exception as e:
        orig_result = f"ERROR: {e}"
    orig_time = time.time() - t0
    print(f" {orig_time:.1f}s")
    
    # 分析压缩图
    print(f"🔵 分析压缩图 {comp_size/1024:.0f}KB...", end="", flush=True)
    t0 = time.time()
    try:
        comp_result = analyze_image(comp_path)
    except Exception as e:
        comp_result = f"ERROR: {e}"
    comp_time = time.time() - t0
    print(f" {comp_time:.1f}s")
    
    # 输出结果
    print(f"\n{'━'*40} 原图分析 ({orig_time:.1f}s) {'━'*40}")
    print(orig_result[:1200])
    print(f"\n{'━'*40} 压缩图分析 ({comp_time:.1f}s) {'━'*40}")
    print(comp_result[:1200])
    
    # 相似度
    orig_words = set(orig_result.lower().split())
    comp_words = set(comp_result.lower().split())
    overlap = orig_words & comp_words
    all_words = orig_words | comp_words
    similarity = len(overlap) / len(all_words) * 100 if all_words else 0
    
    print(f"\n{'━'*40} 对比总结 {'━'*40}")
    print(f"  关键词重叠率: {similarity:.1f}%")
    print(f"  耗时差: {comp_time - orig_time:+.1f}s")
    
    results.append({
        "photo": orig_name,
        "orig_size_mb": round(orig_size/1024/1024, 1),
        "comp_size_kb": round(comp_size/1024, 1),
        "orig_time": round(orig_time, 1),
        "comp_time": round(comp_time, 1),
        "similarity": round(similarity, 1),
        "orig_summary": orig_result[:200],
        "comp_summary": comp_result[:200],
    })

print("\n" + "="*80)
print("📊 总 结")
print("="*80)
for r in results:
    print(f"\n  {r['photo']}:")
    print(f"    原图 {r['orig_size_mb']}MB → 压缩 {r['comp_size_kb']}KB")
    print(f"    分析耗时: 原图 {r['orig_time']}s vs 压缩 {r['comp_time']}s (省 {r['orig_time']-r['comp_time']:.1f}s)")
    print(f"    关键词重叠: {r['similarity']}%")
    print(f"    原图摘要: {r['orig_summary']}")
    print(f"    压缩摘要: {r['comp_summary']}")
print("="*80)
