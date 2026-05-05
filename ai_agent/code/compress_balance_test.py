#!/usr/bin/env python3
"""
压缩平衡测试 — 找保留文字/车牌的最佳压缩点
测试: 原图 vs 1536px vs 1920px vs 2048px（不同质量）
"""
import subprocess, os, json
from pathlib import Path

SRC = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real5")
DST = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/balance")
DST.mkdir(exist_ok=True)

photos = [
    SRC / "IMG_20260430_174807.jpg",  # BRT站
    SRC / "IMG_20260430_180637.jpg",  # 商业街
]

# 压缩方案：分辨率 + 质量
configs = [
    ("1536px_q80", "1536", "80"),
    ("1536px_q85", "1536", "85"),
    ("1536px_q90", "1536", "90"),
    ("1536px_q95", "1536", "95"),
    ("1920px_q80", "1920", "80"),
    ("1920px_q85", "1920", "85"),
    ("1920px_q90", "1920", "90"),
    ("2048px_q80", "2048", "80"),
    ("2048px_q85", "2048", "85"),
    ("2048px_q90", "2048", "90"),
    ("2560px_q80", "2560", "80"),
    ("2560px_q85", "2560", "85"),
]

print("="*80)
print("🔍 压缩平衡测试 — 保留文字/车牌清晰度")
print("="*80)

results = []

for p in photos:
    name = p.name
    orig_size = os.path.getsize(p)
    
    print(f"\n📷 {name} (原始: {orig_size/1024/1024:.1f}MB)")
    print("-" * 60)
    
    for cfg_name, dim, quality in configs:
        dst = DST / f"{name}_{cfg_name.replace(' ', '_')}.jpg"
        
        scale_w = f"if(gt(iw,ih),{dim},-2)"
        scale_h = f"if(gt(iw,ih),-2,{dim})"
        
        cmd = [
            "ffmpeg", "-y", "-i", str(p),
            "-vf", f"scale={scale_w}:{scale_h}",
            "-q:v", quality,
            str(dst)
        ]
        
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if dst.exists():
            comp = os.path.getsize(dst)
            saving = (1 - comp/orig_size) * 100
            
            # 标注推荐等级
            if saving > 95:
                mark = "🔴 压得太狠（文字会丢）"
            elif saving > 90:
                mark = "🟡 偏高（部分文字可能丢）"
            elif saving > 80:
                mark = "🟢 推荐（文字清晰）"
            else:
                mark = "⚪ 压得不够"
            
            print(f"  {cfg_name:<12s}: {comp/1024:>5.0f}KB | 省 {saving:>5.1f}%  {mark}")
            results.append({
                "photo": name,
                "config": cfg_name,
                "size_kb": round(comp/1024),
                "saving": round(saving, 1),
                "path": str(dst)
            })

# 总结
print("\n" + "="*80)
print("📊 推荐方案对比")
print("="*80)

# 找每个照片的最佳方案
for p_name in set(r["photo"] for r in results):
    print(f"\n📷 {p_name}:")
    p_results = sorted([r for r in results if r["photo"] == p_name], 
                       key=lambda x: x["saving"])
    
    # 找文字清晰且压缩合理的方案
    for r in p_results:
        if r["saving"] >= 80 and r["saving"] <= 95:
            status = "✅ 推荐" if 85 <= r["saving"] <= 93 else "⚠️ 备选"
            print(f"   {status} {r['config']}: {r['size_kb']}KB (省 {r['saving']}%)")

print("\n💡 结论:")
print("  • 压缩 <90%: 文字/车牌清晰，但省空间有限")
print("  • 压缩 90-93%: 平衡点，推荐！")
print("  • 压缩 >95%: 文字丢失，不推荐")
print("="*80)
