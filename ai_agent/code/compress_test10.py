#!/usr/bin/env python3
"""10张最近照片批量压缩测试"""
import subprocess, os, json
from pathlib import Path

SRC = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real10")
DST = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real10_compressed")
DST.mkdir(exist_ok=True)

photos = sorted(SRC.glob("IMG_*.jpg"))
total_orig = 0
total_comp = 0
results = []

print("="*80)
print("📸 10张最近照片批量压缩 — 缩放至 1536px")
print("="*80)

for p in photos:
    name = p.name
    orig = os.path.getsize(p)
    total_orig += orig
    
    dst = DST / f"{name}_1536q85.jpg"
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(p),
         "-vf", "scale='if(gt(iw,ih),1536,-2)':'if(gt(iw,ih),-2,1536)'",
         "-q:v", "85", str(dst)],
        capture_output=True, timeout=60
    )
    
    if dst.exists():
        comp = os.path.getsize(dst)
        total_comp += comp
        saving = (1 - comp/orig) * 100
        results.append({"name": name, "orig": orig, "comp": comp, "saving": saving})
        print(f"  ✅ {name}: {orig/1024/1024:.1f}MB → {comp/1024:.0f}KB | 省 {saving:.1f}%")
    else:
        print(f"  ❌ {name}: 失败")

print(f"\n📊 总计: {total_orig/1024/1024:.0f}MB → {total_comp/1024/1024:.2f}MB")
print(f"   压缩比: {(1-total_comp/total_orig)*100:.1f}% | 节省 {total_orig/1024/1024 - total_comp/1024/1024:.1f}MB")
print("="*80)

# 保存报告
with open(DST / "compress_report.json", "w") as f:
    json.dump({
        "count": len(results),
        "total_original_mb": round(total_orig/1024/1024, 1),
        "total_compressed_mb": round(total_comp/1024/1024, 2),
        "ratio_pct": round((1-total_comp/total_orig)*100, 1),
        "saved_mb": round((total_orig-total_comp)/1024/1024, 1),
        "details": [{"name": r["name"], "orig_kb": round(r["orig"]/1024), "comp_kb": round(r["comp"]/1024), "saving_pct": round(r["saving"],1)} for r in results]
    }, f, indent=2)
print(f"报告: {DST}/compress_report.json")
