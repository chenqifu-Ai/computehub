#!/usr/bin/env python3
"""真实照片压缩测试 - 5 张 5-6点半拍的照片"""
import subprocess, os, json, time
from pathlib import Path

SRC_DIR = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real5")
DST_DIR = Path("/root/.openclaw/workspace/ai_agent/results/compress_test/real5_compressed")
DST_DIR.mkdir(exist_ok=True)

photos = sorted(SRC_DIR.glob("IMG_20260430_1*.jpg"))[:5]

def compress_jpg(src, dst, quality=85):
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", "scale='if(gt(iw,ih),1536,-2)':'if(gt(iw,ih),-2,1536)'",
        "-q:v", str(quality),
        str(dst)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode == 0

def get_dims(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=10
    )
    try:
        d = json.loads(r.stdout)
        return int(d["streams"][0]["width"]), int(d["streams"][0]["height"])
    except:
        return 0, 0

print("="*80)
print("📸 真实照片压缩测试 — 5 张 17:48~18:06 的照片")
print("="*80)

total_original = 0
total_compressed = 0

for p in photos:
    name = p.name
    orig_size = os.path.getsize(p)
    w, h = get_dims(p)
    total_original += orig_size
    
    print(f"\n📷 {name}")
    print(f"   原始: {orig_size/1024/1024:.1f}MB | {w}x{h}")
    
    # 1536px
    dst_1536 = DST_DIR / f"{name}_1536q85.jpg"
    if compress_jpg(p, dst_1536, 85) and dst_1536.exists():
        c1 = os.path.getsize(dst_1536)
        s1, s2 = get_dims(dst_1536)
        saving1 = (1 - c1/orig_size) * 100
        total_compressed += c1
        print(f"   1536px: {c1/1024:.1f}KB | {s1}x{s2} | 省 {saving1:.1f}% ✅")
    else:
        print(f"   1536px: 失败 ❌")
    
    # 1920px
    dst_1920 = DST_DIR / f"{name}_1920q85.jpg"
    cmd = [
        "ffmpeg", "-y", "-i", str(p),
        "-vf", "scale='if(gt(iw,ih),1920,-2)':'if(gt(iw,ih),-2,1920)'",
        "-q:v", "85",
        str(dst_1920)
    ]
    if subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0 and dst_1920.exists():
        c2 = os.path.getsize(dst_1920)
        s1, s2 = get_dims(dst_1920)
        saving2 = (1 - c2/orig_size) * 100
        total_compressed += c2
        print(f"   1920px: {c2/1024:.1f}KB | {s1}x{s2} | 省 {saving2:.1f}% ✅")
    else:
        print(f"   1920px: 失败 ❌")

print("\n" + "="*80)
print(f"📊 总计: 原始 {total_original/1024/1024:.1f}MB → 1536px {total_compressed/1024/1024:.2f}MB")
print(f"   压缩比: {(1 - total_compressed/total_original)*100:.1f}%")
print(f"   节省: {total_original/1024/1024 - total_compressed/1024/1024:.1f}MB")
print(f"   结果目录: {DST_DIR}")
print("="*80)
