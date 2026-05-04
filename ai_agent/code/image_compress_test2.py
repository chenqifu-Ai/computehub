#!/usr/bin/env python3
"""图片压缩测试2 - WebP 参数调优"""
import subprocess, os, json, time
from pathlib import Path

SRC = Path("/root/.openclaw/workspace/_temp_video_frames/frame_01_2s.jpg")
SRC2 = Path("/root/.openclaw/workspace/_temp_image_recognition/mmexport1777511387238.jpg")
RESULTS_DIR = Path("/root/.openclaw/workspace/ai_agent/results/compress_test")

def compress(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0

def fmt(b):
    if b < 1024: return f"{b}B"
    elif b < 1024*1024: return f"{b/1024:.1f}KB"
    return f"{b/1024/1024:.2f}MB"

print("原始文件对比:")
print(f"  视频帧: {fmt(os.path.getsize(SRC))} | {SRC.name}")
print(f"  截图:   {fmt(os.path.getsize(SRC2))} | {SRC2.name}")
print()

scales = [
    ("1536px质量", "scale='if(gt(iw,ih),1536,-2)':'if(gt(iw,ih),-2,1536)'"),
    ("2048px质量", "scale='if(gt(iw,ih),2048,-2)':'if(gt(iw,ih),-2,2048)'"),
    ("1920px均衡", "scale='if(gt(iw,ih),1920,-2)':'if(gt(iw,ih),-2,1920)'"),
]

configs = [
    ("jpeg_q85",   "jpg",  "-q:v", "85"),
    ("jpeg_q75",   "jpg",  "-q:v", "75"),
    ("jpeg_q65",   "jpg",  "-q:v", "65"),
    ("webp_q80",   "webp", "-q:v", "80"),
    ("webp_q90",   "webp", "-q:v", "90"),
    ("webp_lossless", "webp", "-lossless", "1"),
    ("webp_q95",   "webp", "-q:v", "95"),
]

print("="*80)
print("📸 测试图1: 视频帧 (3840x2160 → 原文件 ~765KB)")
print("="*80)

for scale_name, scale_filter in scales:
    print(f"\n--- 缩放: {scale_name} ---")
    for cfg_name, ext, flag, val in configs:
        dst = RESULTS_DIR / f"frame01_{scale_name}_{cfg_name}.{ext}"
        cmd = ["ffmpeg", "-y", "-i", str(SRC), "-vf", scale_filter, flag, val, str(dst)]
        if compress(cmd) and dst.exists():
            size = os.path.getsize(dst)
            ratio = (1 - size/765000) * 100
            print(f"  {cfg_name:20s}: {fmt(size):>8s} | 省 {ratio:>5.1f}%")

print()
print("="*80)
print("📸 测试图2: 手机截图 (1080x1919 → 原文件 ~388KB)")
print("="*80)

for scale_name, scale_filter in scales:
    print(f"\n--- 缩放: {scale_name} ---")
    for cfg_name, ext, flag, val in configs:
        dst = RESULTS_DIR / f"mm_{scale_name}_{cfg_name}.{ext}"
        cmd = ["ffmpeg", "-y", "-i", str(SRC2), "-vf", scale_filter, flag, val, str(dst)]
        if compress(cmd) and dst.exists():
            size = os.path.getsize(dst)
            ratio = (1 - size/388000) * 100
            print(f"  {cfg_name:20s}: {fmt(size):>8s} | 省 {ratio:>5.1f}%")

print()
print("结果已保存至:", RESULTS_DIR)
