#!/usr/bin/env python3
"""
视频帧分析流程
视频 → ffmpeg 抽取关键帧 → qwen3-vl:235b 分析 → 汇总结果

规范: VIDEO-FRAME-001
"""
import subprocess, requests, json, time, base64, os, sys, tempfile

# ========== 配置 ==========
OLLAMA_CLOUD_URL = "https://ollama.com/v1/chat/completions"
OLLAMA_API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
VISION_MODEL = "qwen3-vl:235b"
FRAMES_COUNT = 5  # 默认抽取帧数
OUTPUT_DIR = "/tmp/video_frames"

def extract_frames(video_path, count=FRAMES_COUNT, output_dir=OUTPUT_DIR):
    """从视频中均匀抽取 N 帧"""
    if not os.path.exists(video_path):
        return [], f"❌ 视频文件不存在: {video_path}"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取视频时长
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_entries", "format=duration", video_path],
            capture_output=True, text=True, timeout=30
        )
        duration = json.loads(probe.stdout)["format"]["duration"]
    except Exception as e:
        return [], f"❌ 无法获取视频信息: {e}"
    
    print(f"📹 视频: {video_path}")
    print(f"   时长: {duration:.1f}s")
    print(f"   抽取: {count} 帧")
    
    frame_paths = []
    interval = duration / (count + 1)
    
    for i in range(1, count + 1):
        t = int(interval * i)
        frame_file = os.path.join(output_dir, f"frame_{i:02d}_{t}s.jpg")
        
        # 抽取单帧
        cmd = [
            "ffmpeg", "-y", "-ss", str(t), "-i", video_path,
            "-vframes", "1", "-q:v", "2", frame_file
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        
        if os.path.exists(frame_file):
            size = os.path.getsize(frame_file) / 1024
            frame_paths.append((frame_file, f"第{i}帧 {t}s ({size:.0f}KB)"))
            print(f"   ✅ 帧{i}: {t}s - {frame_file} ({size:.0f}KB)")
        else:
            print(f"   ❌ 帧{i}: 抽取失败")
    
    return frame_paths, "✅ 帧抽取完成"


def analyze_frame_with_vl(frame_path, prompt="请详细描述这张图片的内容"):
    """使用 qwen3-vl:235b 分析单帧图片"""
    try:
        with open(frame_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"❌ 读取图片失败: {e}"
    
    # 构建 Ollama API 请求
    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [b64],
        "stream": False
    }
    
    start = time.time()
    try:
        r = requests.post(
            f"{OLLAMA_CLOUD_URL}/chat",
            json=payload,
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
            timeout=120
        )
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            content = data.get("message", {}).get("content", "")
            if content:
                print(f"   ⏱ {(elapsed*1000):.0f}ms | ✅ 分析成功")
                return content
            else:
                return "⚠️ 模型返回空内容"
        else:
            return f"❌ HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"❌ 请求失败: {e}"


def analyze_video(video_path, frames=FRAMES_COUNT, prompt=""):
    """完整视频分析流程"""
    if not prompt:
        prompt = "请详细描述这张图片中的所有内容，包括场景、物体、人物、文字、动作等。"
    
    print(f"\n{'='*60}")
    print(f"  🎬 视频帧分析流程")
    print(f"  视频: {video_path}")
    print(f"  模型: {VISION_MODEL}")
    print(f"{'='*60}\n")
    
    # Step 1: 抽取帧
    frame_list, step1_result = extract_frames(video_path, frames)
    print(f"\n{step1_result}")
    
    if not frame_list:
        return {"error": "帧抽取失败"}
    
    # Step 2: 分析每一帧
    print(f"\n--- 开始分析 {len(frame_list)} 帧 ---\n")
    
    results = []
    for frame_file, frame_info in frame_list:
        print(f"\n[帧] {frame_info}")
        analysis = analyze_frame_with_vl(frame_file, prompt)
        results.append({
            "frame": frame_info,
            "analysis": analysis
        })
    
    # Step 3: 汇总
    print(f"\n{'='*60}")
    print(f"  📊 分析汇总")
    print(f"{'='*60}\n")
    
    for r in results:
        print(f"  --- {r['frame']} ---")
        print(f"  {r['analysis']}\n")
    
    summary = {
        "video": video_path,
        "frames_analyzed": len(results),
        "model": VISION_MODEL,
        "frames": results
    }
    
    return summary


def main():
    if len(sys.argv) < 2:
        print("用法: python3 video_frame_analysis.py <视频路径> [帧数]")
        print()
        print("示例:")
        print("  python3 video_frame_analysis.py /path/to/video.mp4")
        print("  python3 video_frame_analysis.py /path/to/video.mp4 10")
        print()
        print("可用模型: qwen3-vl:235b")
        sys.exit(1)
    
    video_path = sys.argv[1]
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else FRAMES_COUNT
    
    result = analyze_video(video_path, frames)
    
    # 保存到文件
    out_file = f"{OUTPUT_DIR}/analysis_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n📁 结果已保存到: {out_file}")


if __name__ == "__main__":
    main()
