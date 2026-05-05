#!/usr/bin/env python3
"""
不同压缩档次对比测试 — 保留车牌/文字清晰度
对比: 1536px q85 vs q90 vs q95 vs 2048px q85 vs q90
"""
import subprocess, os, json
from pathlib import Path

SRC = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real5")
DST = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/different_levels")
DST.mkdir(exist_ok=True)

# 选一张有文字信息的照片测试
photos = [
    SRC / "IMG_20260430_174807.jpg",  # BRT站 - 有小字站牌
    SRC / "IMG_20260430_180637.jpg",  # 商业街 - 有招牌文字
]

configs = [
    ("1536px_q85",   "1536",   "85"),
    ("1536px_q90",   "1536",   "90"),
    ("1536px_q95",   "1536",   "95"),
    ("1920px_q85",   "1920",   "85"),
    ("1920px_q90",   "1920",   "90"),
    ("1920px_q95",   "1920",   "95"),
    ("2048px_q85",   "2048",   "85"),
    ("2048px_q90",   "2048",   "90"),
    ("2048px_q95",   "2048",   "95"),
    ("原图对比",     "original", ""),
]

print("="*90)
print("🔍 不同压缩档次对比 — 重点看小字/车牌清晰度")
print("="*90)

results = {}

for p in photos:
    name = p.name
    orig_size = os.path.getsize(p)
    
    print(f"\n{'='*60}")
    print(f"📷 {name} (原始: {orig_size/1024/1024:.1f}MB)")
    print(f"{'='*60}")
    
    results[name] = {}
    
    for cfg_name, dim, quality in configs:
        if cfg_name == "原图对比":
            results[name][cfg_name] = {"size": orig_size, "path": str(p)}
            print(f"  {'原图':<12s}: {orig_size/1024/1024:>6.1f}MB  {'(原始)'}")
            continue
        
        dst = DST / f"{name}_{cfg_name}.jpg"
        
        # 构建缩放参数
        if dim == "1536":
            scale = "if(gt(iw,ih),1536,-2)" if 'q' in cfg_name else "-2"
            scale_h = "if(gt(iw,ih),-2,1536)"
            scale_filter = f"scale='{scale}':'{scale_h}'"
        elif dim == "1920":
            scale = "if(gt(iw,ih),1920,-2)"
            scale_h = "if(gt(iw,ih),-2,1920)"
            scale_filter = f"scale='{scale}':'{scale_h}'"
        elif dim == "2048":
            scale = "if(gt(iw,ih),2048,-2)"
            scale_h = "if(gt(iw,ih),-2,2048)"
            scale_filter = f"scale='{scale}':'{scale_h}'"
        
        cmd = ["ffmpeg", "-y", "-i", str(p), "-vf", scale_filter, "-q:v", quality, str(dst)]
        subprocess.run(cmd, capture_output=True, timeout=60)
        
        if dst.exists():
            size = os.path.getsize(dst)
            saving = (1 - size/orig_size) * 100
            results[name][cfg_name] = {"size": size, "path": str(dst)}
            print(f"  {cfg_name:<12s}: {size/1024:>6.0f}KB | 省 {saving:>5.1f}%")
        else:
            print(f"  {cfg_name:<12s}: 失败")

# 保存报告
report_data = {}
for name, configs in results.items():
    report_data[name] = {}
    for cfg, info in configs.items():
        report_data[name][cfg] = {
            "size_kb": round(info["size"]/1024),
            "size_mb": round(info["size"]/1024/1024, 2),
            "path": os.path.basename(info["path"])
        }

with open(DST / "different_levels_report.json", "w") as f:
    json.dump(report_data, f, indent=2, ensure_ascii=False)

print(f"\n{'='*90}")
print("📊 结果保存: DST/different_levels_report.json")
print("="*90)
