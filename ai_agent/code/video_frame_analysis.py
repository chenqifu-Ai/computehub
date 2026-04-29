#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频帧分析标准流程 v1.0
========================
功能：ffmpeg 抽帧 + AI 视觉模型分析
调用方式：python3 video_frame_analysis.py <视频路径> [--frames N] [--model 235b|8b]

配置：
  - 模型：qwen3-vl:235b（高精度~45s/帧）或 qwen3-vl:8b（快速~5s/帧）
  - API：https://ollama.com/api/generate
  - 输出：results/video_frame_analysis/

用法：
  python3 video_frame_analysis.py <视频文件>
  python3 video_frame_analysis.py test.mp4 --frames 3 --duration 3
  python3 video_frame_analysis.py test.mp4 --model 8b  # 快速模式
"""

import subprocess
import sys
import os
import json
import base64
import time
import argparse
from pathlib import Path
from datetime import datetime

# ===== 配置 =====
OUTPUT_DIR = Path(__file__).parent.parent / "results" / "video_frame_analysis"
TEMP_DIR = Path(__file__).parent.parent / "data" / "temp_frames"
API_URL = "https://ollama.com/api/generate"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
MODELS = {
    "235b": "qwen3-vl:235b",      # 高精度 ~45s/帧
    "8b": "qwen3-vl:8b",           # 快速 ~5s/帧
}
DEFAULT_MODEL = "235b"
DEFAULT_FRAMES = 3
DEFAULT_VIDEO_DURATION = 3  # 秒


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def extract_frames(video_path: str, num_frames: int, duration: float) -> list:
    """ffmpeg 从视频中抽取指定帧"""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    # 获取视频时长
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video_path)],
        capture_output=True, text=True, timeout=10
    )
    actual_duration = float(probe.stdout.strip()) if probe.stdout.strip() else duration
    print(f"  视频时长: {actual_duration:.1f}s")

    frame_paths = []
    for i in range(num_frames):
        if num_frames == 1:
            t = 0
        else:
            safe_dur = min(duration - 0.1, actual_duration - 0.1)
            t = (i / (num_frames - 1)) * max(safe_dur, 0)

        ts = f"{t:.1f}"
        name = f"frame_{i+1:02d}_{ts}s.jpg"
        path = TEMP_DIR / name

        cmd = ["ffmpeg", "-ss", ts, "-i", str(video_path),
               "-vframes", "1", "-q:v", "2", "-y", str(path)]
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0 and path.exists() and path.stat().st_size > 100:
            frame_paths.append(str(path))
            print(f"  ✅ 帧 {i+1:02d} (t={ts}s) {path.stat().st_size}B")
        else:
            print(f"  ❌ 帧 {i+1:02d} (t={ts}s) 失败")

    return frame_paths


def analyze_frame(frame_path: str, prompt: str, model: str, max_retries: int = 2) -> dict:
    """AI 视觉模型分析单帧图片"""
    if not prompt:
        prompt = ("请用中文描述：1.场景 2.主要物体和颜色 3.图案纹理 4.画面构图")

    with open(frame_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    for attempt in range(max_retries + 1):
        try:
            payload = {
                "model": MODELS[model],
                "stream": True,
                "prompt": prompt,
                "images": [img_b64]
            }
            start = time.time()
            resp = requests.post(API_URL, json=payload, headers=headers,
                                 stream=True, timeout=120)

            if resp.status_code == 200:
                full_text = ""
                for line in resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if chunk.get("done"):
                                break
                            full_text += chunk.get("response", "")
                        except:
                            pass

                elapsed = time.time() - start
                return {"success": True, "elapsed": elapsed,
                        "content": full_text.strip(),
                        "name": Path(frame_path).name}
            else:
                print(f"  ⚠️ HTTP {resp.status_code} (尝试{attempt+1})")
                time.sleep(2)

        except Exception as e:
            print(f"  ❌ 错误 (尝试{attempt+1}): {e}")
            time.sleep(min(2 ** attempt, 10))

    return {"success": False, "elapsed": 0, "content": "",
            "error": "分析失败", "name": Path(frame_path).name}


def analyze_video(video_path: str, num_frames: int, duration: float,
                  model: str = DEFAULT_MODEL, prompt: str = None) -> dict:
    """
    完整视频帧分析流程
    
    Args:
        video_path: 视频文件路径
        num_frames: 抽取帧数
        duration: 分析时长（秒）
        model: 模型 235b 或 8b
        prompt: 自定义提示词
    
    Returns:
        dict: 分析结果
    """
    print("=" * 60)
    print("🎬 视频帧分析标准流程")
    print("=" * 60)
    print(f"  视频: {video_path}")
    print(f"  模型: {MODELS[model]}")
    print(f"  抽帧: {num_frames}帧 / {duration}秒")
    print("=" * 60)

    ensure_dirs()
    total_start = time.time()

    # Step 1: 抽帧
    print("\n📸 步骤1: ffmpeg 抽帧")
    frame_paths = extract_frames(video_path, num_frames, duration)
    if not frame_paths:
        print("❌ 抽帧失败")
        return None
    print(f"  ✅ 成功 {len(frame_paths)} 帧\n")

    # Step 2: AI 分析
    print("🧠 步骤2: AI 视觉分析")
    results = []
    for i, fp in enumerate(frame_paths):
        print(f"\n  📷 帧 {i+1}/{len(frame_paths)}: {Path(fp).name}")
        result = analyze_frame(fp, prompt, model)
        result["index"] = i + 1
        results.append(result)
        if result["success"]:
            print(f"     ⏱️ {result['elapsed']:.1f}s | {result['content'][:60]}...")
        else:
            print(f"     ❌ {result.get('error','')}")

    # Step 3: 汇总
    total_elapsed = time.time() - total_start
    success_count = sum(1 for r in results if r["success"])

    print("\n" + "=" * 60)
    print("📊 结果汇总")
    print("=" * 60)
    print(f"{'帧':<8} {'耗时':<10} {'描述'}")
    print("-" * 60)
    for r in results:
        idx = r["index"]
        ts = r["name"].split("_")[1].replace("s", "") if "_" in r["name"] else ""
        elapsed = f"{r['elapsed']:.1f}s" if r["success"] else "N/A"
        desc = r["content"][:40].replace("\n", " ") if r["success"] else r.get("error", "失败")
        print(f"帧{idx:02d}({ts}s)  {elapsed:<6} │ {desc}")
    print("-" * 60)
    print(f"  总耗时: {total_elapsed:.1f}s")
    print(f"  成功: {success_count}/{len(results)}")
    print("=" * 60)

    # 保存结果
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = OUTPUT_DIR / f"analysis_{ts}.json"
    output = {
        "video": video_path,
        "model": MODELS[model],
        "frames": len(results),
        "total_elapsed": total_elapsed,
        "results": results,
        "timestamp": ts
    }
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 结果: {result_file}")

    return output


def main():
    p = argparse.ArgumentParser(description="视频帧分析标准流程")
    p.add_argument("video", help="视频文件路径")
    p.add_argument("--frames", "-n", type=int, default=DEFAULT_FRAMES,
                   help=f"帧数 (默认:{DEFAULT_FRAMES})")
    p.add_argument("--duration", "-d", type=float, default=DEFAULT_VIDEO_DURATION,
                   help=f"时长秒 (默认:{DEFAULT_VIDEO_DURATION})")
    p.add_argument("--model", choices=["235b", "8b"], default=DEFAULT_MODEL,
                   help=f"模型: 235b(高精度) 8b(快速)")
    p.add_argument("--prompt", "-p", type=str, default=None,
                   help="自定义分析提示词")
    args = p.parse_args()

    analyze_video(args.video, args.frames, args.duration, args.model, args.prompt)


if __name__ == "__main__":
    import requests
    main()
