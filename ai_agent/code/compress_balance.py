#!/usr/bin/env python3
"""
压缩平衡测试 — 找保留文字/车牌的最佳压缩点
用 -q:v 参数 (范围 2-31, 2=最好, 31=最差)
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

# 测试方案：缩放 + 质量 (-q:v 范围 2-31, 越小质量越高)
# q=5: 高质量 ~90% 节省
# q=10: 中等 ~95% 节省
# q=15: 较低 ~97% 节省
configs = [
    ("1536_q5",   1536, 5),    # 高质量
    ("1536_q8",   1536, 8),
    ("1536_q10",  1536, 10),
    ("1536_q12",  1536, 12),
    ("1536_q15",  1536, 15),
    ("1536_q20",  1536, 20),
    ("1920_q5",   1920, 5),
    ("1920_q8",   1920, 8),
    ("1920_q10",  1920, 10),
    ("1920_q12",  1920, 12),
    ("1920_q15",  1920, 15),
    ("2048_q5",   2048, 5),
    ("2048_q8",   2048, 8),
    ("2048_q10",  2048, 10),
    ("2048_q12",  2048, 12),
    ("2048_q15",  2048, 15),
    ("2048_q20",  2048, 20),
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
    
    for cfg_name, dim, qv in configs:
        dst = DST / f"{name}_{cfg_name}.jpg"
        
        scale = f"'if(gt(iw,ih),{dim},-2)':'if(gt(iw,ih),-2,{dim})'"
        
        cmd = [
            "ffmpeg", "-y", "-i", str(p),
            "-vf", f"scale={scale}",
            "-q:v", str(qv),
            "-update", "1",
            str(dst)
        ]
        
        print(f"  压缩 {cfg_name}...", end="", flush=True)
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if dst.exists():
            comp = os.path.getsize(dst)
            saving = (1 - comp/orig_size) * 100
            
            # 标注推荐等级
            if saving > 97:
                mark = "🔴 压太狠（文字会丢）"
            elif saving > 95:
                mark = "🟡 偏高（部分文字可能丢）"
            elif saving > 90:
                mark = "🟢 推荐（文字清晰）"
            else:
                mark = "⚪ 压得不够"
            
            print(f" {comp/1024:>5.0f}KB | 省 {saving:>5.1f}%  {mark}")
            results.append({
                "photo": name,
                "config": cfg_name,
                "size_kb": round(comp/1024),
                "saving": round(saving, 1),
                "qv": qv,
                "path": str(dst)
            })
        else:
            print(f" 失败: {r.stderr.decode()[:100]}")

# 总结
print("\n" + "="*80)
print("📊 推荐方案")
print("="*80)

for p_name in set(r["photo"] for r in results):
    print(f"\n📷 {p_name}:")
    p_results = sorted([r for r in results if r["photo"] == p_name], 
                       key=lambda x: x["size_kb"])
    
    for r in p_results:
        if 85 <= r["saving"] <= 96:
            status = "✅ 推荐" if 88 <= r["saving"] <= 95 else "⚠️ 备选"
            print(f"   {status} {r['config']}: {r['size_kb']}KB (省 {r['saving']}%, q={r['qv']})")

print("\n💡 建议:")
print("  • 需要看清车牌/小字: 选 q10-q12（省 90-95%）")
print("  • 只看场景不需要文字: 选 q15+（省 95%+）")
print("="*80)
