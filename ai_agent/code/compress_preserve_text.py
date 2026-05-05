#!/usr/bin/env python3
"""
保留文字/车牌清晰度的压缩处理
方案: 1920px q5 (省~93%, 文字清晰)
"""
import subprocess, os, json
from pathlib import Path

SRC = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real5")
DST = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/preserve_text")
DST.mkdir(exist_ok=True)

photos = sorted(SRC.glob("IMG_*.jpg"))

print("=" * 80)
print("🔍 保留文字/车牌清晰度 — 重新压缩")
print("方案: 1920px q5 (文字清晰, 省 ~93%)")
print("=" * 80)

results = []

for p in photos:
    name = p.name
    orig_size = os.path.getsize(p)
    print(f"\n📷 {name} (原始: {orig_size/1024/1024:.1f}MB)")
    
    for dim, qv, label in [(1920, 5, "1920px_q5"), (1536, 5, "1536px_q5")]:
        ext = f"_{dim}_{qv}.jpg"
        dst = DST / f"{name.replace('.jpg', ext)}"
        
        # 用简单的 scale 参数
        w = dim if dim <= p.stat().st_size else -2  # 占位
        scale = f"scale={dim}:-2"
        
        cmd = ["ffmpeg", "-y", "-i", str(p), "-vf", scale, "-q:v", str(qv), "-update", "1", str(dst)]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if dst.exists() and dst.stat().st_size > 0:
            size = dst.stat().st_size
            saving = (1 - size/orig_size) * 100
            print(f"  ✅ {label}: {size/1024:>5.0f}KB (省 {saving:.1f}%)")
            results.append({
                "photo": name,
                "config": label,
                "orig_mb": round(orig_size/1024/1024, 1),
                "comp_kb": round(size/1024),
                "saving": round(saving, 1),
            })
        else:
            err = r.stderr.decode()[:200] if r.stderr else "unknown"
            print(f"  ❌ {label}: 失败 - {err}")

# 总结
print("\n" + "=" * 80)
print("📊 压缩结果")
print("=" * 80)

# 按照片分组
for photo in set(r["photo"] for r in results):
    photo_results = [r for r in results if r["photo"] == photo]
    print(f"\n{photo} (原图 {photo_results[0]['orig_mb']}MB):")
    for r in photo_results:
        print(f"  {r['config']}: {r['comp_kb']}KB (省 {r['saving']}%)")

print(f"\n✅ 结果保存目录: {DST}/")
print("=" * 80)
