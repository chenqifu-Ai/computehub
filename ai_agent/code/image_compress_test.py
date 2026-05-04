#!/usr/bin/env python3
"""图片压缩测试：缩放至 1536px + 质量压缩"""
import subprocess
import os
import json
import time
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
RESULTS_DIR = WORKSPACE / "ai_agent/results"

# 候选图片列表（大文件优先）
TEST_IMAGES = [
    WORKSPACE / "stock_check.jpg",
    WORKSPACE / "_temp_image_recognition/mmexport1777511387238.jpg",
    WORKSPACE / "_temp_image_recognition/wx_camera_1777511202166.jpg",
]

# 额外：video frames 抽几个测试
for f in sorted((WORKSPACE / "_temp_video_frames").glob("*.jpg"))[:3]:
    TEST_IMAGES.append(f)

RESULTS = []

def get_size(path):
    return os.path.getsize(path)

def format_size(b):
    if b < 1024:
        return f"{b}B"
    elif b < 1024*1024:
        return f"{b/1024:.1f}KB"
    else:
        return f"{b/1024/1024:.2f}MB"

def get_dimensions(path):
    """用 ffprobe 获取图片尺寸"""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=10
    )
    try:
        data = json.loads(r.stdout)
        s = data["streams"][0]
        return int(s["width"]), int(s["height"])
    except:
        return 0, 0

def compress_image(src, dst, max_dim=1536, quality=82):
    """ffmpeg 压缩：缩放至 max_dim + 质量压缩"""
    scale = f"scale='if(gt(iw,ih),{max_dim},-2)':'if(gt(iw,ih),-2,{max_dim})'"
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", scale,
        "-q:v", str(quality),  # JPEG quality
        str(dst)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0

def compress_to_webp(src, dst, max_dim=1536, quality=80):
    """转为 WebP 压缩"""
    scale = f"scale='if(gt(iw,ih),{max_dim},-2)':'if(gt(iw,ih),-2,{max_dim})'"
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", scale,
        "-q:v", str(quality),
        str(dst)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0

print("="*70)
print("🖼️  图片压缩测试 — 缩放至 1536px")
print("="*70)

COMPRESS_DIR = RESULTS_DIR / "compress_test"
COMPRESS_DIR.mkdir(parents=True, exist_ok=True)

test_count = 0
for img_path in TEST_IMAGES:
    if not img_path.exists():
        continue
    test_count += 1
    original_size = get_size(img_path)
    w, h = get_dimensions(img_path)
    
    print(f"\n[{test_count}] {img_path.name}")
    print(f"    原始: {format_size(original_size)} | {w}x{h}")
    
    # 方案1: JPEG 缩放 + 质量压缩
    jpeg_dst = COMPRESS_DIR / f"{img_path.stem}_1536q82.jpg"
    ok = compress_image(img_path, jpeg_dst, max_dim=1536, quality=82)
    if ok and jpeg_dst.exists():
        jpeg_size = get_size(jpeg_dst)
        ratio = (1 - jpeg_size/original_size) * 100
        print(f"    JPEG: {format_size(jpeg_size)} | 压缩 {ratio:.1f}% ✅")
        
        # 方案2: WebP 缩放 + 质量压缩
        webp_dst = COMPRESS_DIR / f"{img_path.stem}_1536q80.webp"
        ok2 = compress_to_webp(img_path, webp_dst, max_dim=1536, quality=80)
        if ok2 and webp_dst.exists():
            webp_size = get_size(webp_dst)
            webp_ratio = (1 - webp_size/original_size) * 100
            print(f"    WebP: {format_size(webp_size)} | 压缩 {webp_ratio:.1f}% ✅")
            print(f"    WebP vs JPEG: {format_size(webp_size)} vs {format_size(jpeg_size)}")
            RESULTS.append({
                "file": img_path.name,
                "original_size": original_size,
                "jpeg_size": jpeg_size,
                "webp_size": webp_size,
                "jpeg_ratio": round(ratio, 1),
                "webp_ratio": round(webp_ratio, 1),
            })
        else:
            RESULTS.append({
                "file": img_path.name,
                "original_size": original_size,
                "jpeg_size": jpeg_size,
                "webp_size": None,
                "jpeg_ratio": round(ratio, 1),
                "webp_ratio": None,
            })
    else:
        print(f"    JPEG: 失败 ❌")

print("\n" + "="*70)
print(f"测试完成: {test_count} 张图片")
print(f"结果保存: {COMPRESS_DIR}")

# 总结
if RESULTS:
    total_original = sum(r["original_size"] for r in RESULTS)
    total_jpeg = sum(r["jpeg_size"] for r in RESULTS)
    total_webp = sum(r["webp_size"] for r in RESULTS if r["webp_size"])
    
    print(f"\n📊 总体对比:")
    print(f"    原始总计:   {format_size(total_original)}")
    print(f"    JPEG 总计:  {format_size(total_jpeg)} | 省 {((1-total_jpeg/total_original)*100):.1f}%")
    if total_webp:
        print(f"    WebP 总计:  {format_size(total_webp)} | 省 {((1-total_webp/total_original)*100):.1f}%")
    
    # 保存报告
    report = {
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "max_dim": 1536,
        "jpeg_quality": 82,
        "webp_quality": 80,
        "results": RESULTS,
        "summary": {
            "total_original": total_original,
            "total_jpeg": total_jpeg,
            "total_webp": total_webp,
            "jpeg_saving_pct": round((1-total_jpeg/total_original)*100, 1),
            "webp_saving_pct": round((1-total_webp/total_original)*100, 1),
        }
    }
    report_path = COMPRESS_DIR / "compress_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"    报告: {report_path}")
