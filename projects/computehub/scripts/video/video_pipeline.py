#!/usr/bin/env python3
"""
🎬 ComputeHub 视频编码引擎 — 重构版

修复记录 (2026-05-16):
  #1  moviepy.editor 被移除 → from moviepy import ImageClip
  #2  .set_duration() → .with_duration() API 迁移
  #3  PIL rectangle((60,150),(8,...)) 坐标反了 → 正序 (x1,y1,x2,y2)
  #4  YUV管道编码输出0字节 → 改用 -loop 1 -i png
  #5  -loop 1 位置放错 → 必须 -loop 1 -i 顺序
  #6  AAC编码浏览器不兼容 → 统一 MP3 编码
  #7  ffprobe 返回 duration=7.24 不是纯数字 → re.search() 提取
  #8  Gateway API \\n 被转义 → 脚本内置不传代码
  #9  Gateway 30s 超时 → nohup 后台执行 + 进度文件
  #10 节点频繁offline → 心跳守护进程 (Worker 内置)
  #11 30个worker资源浪费 → 限定并发
  #12 27页×30MB临时文件 → 生成完清理 + 磁盘上限检测

用法:
  python3 video_pipeline.py \\
    --doc /path/to/file.pptx \\
    --output /tmp/output.mp4 \\
    --template business \\
    --voice yunxi \\
    --mode auto
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

# ── 内部模块 ──────────────────────────────────────────────────
# scripts/video/ 下的模块，Worker 内置
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

import doc_parser
import tts_engine

# ── 常量 ──────────────────────────────────────────────────────

OUTPUT_DIR = "/var/computehub/gallery"
WORK_DIR_BASE = "/tmp/computehub-video"
MAX_PAGES = 50          # 单次最多 50 页
MAX_DISK_MB = 500       # 磁盘上限 500MB
MAX_CONCURRENT = 3      # 修复 #11: 限制并发

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(WORK_DIR_BASE, exist_ok=True)


# ── 进度报告 ──────────────────────────────────────────────────

class ProgressReporter:
    """写进度文件，供 Worker/API 轮询读取"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.progress_dir = os.path.join(WORK_DIR_BASE, "progress")
        os.makedirs(self.progress_dir, exist_ok=True)
        self.progress_file = os.path.join(self.progress_dir, f"{task_id}.json")
        self._report("init", 0, "任务初始化")

    def _report(self, stage: str, pct: int, msg: str):
        data = {
            "task_id": self.task_id,
            "stage": stage,
            "percent": pct,
            "message": msg,
            "timestamp": time.time(),
        }
        with open(self.progress_file, "w") as f:
            json.dump(data, f, ensure_ascii=False)

    def parsing(self, pct=5):
        self._report("parsing", pct, "解析文档")

    def rendering(self, current: int, total: int):
        pct = 10 + int(60 * current / total)
        self._report("rendering", min(pct, 70), f"渲染页面 {current}/{total}")

    def tts(self, current: int, total: int):
        pct = 70 + int(15 * current / total)
        self._report("tts", min(pct, 85), f"生成语音 {current}/{total}")

    def encoding(self, pct=90):
        self._report("encoding", pct, "编码视频")

    def uploading(self, pct=95):
        self._report("uploading", pct, "上传 Gallery")

    def done(self, output_path: str):
        self._report("done", 100, f"完成: {output_path}")

    def error(self, msg: str):
        self._report("error", -1, msg)


# ── 磁盘管理 ──────────────────────────────────────────────────

def check_disk_space(path: str, max_mb: int = MAX_DISK_MB) -> bool:
    """检查磁盘空间，超限则拒绝"""
    try:
        st = os.statvfs(path)
        available = st.f_frsize * st.f_bavail / 1024 / 1024
        if available < max_mb:
            print(f"  ⚠️ 磁盘可用空间不足: {available:.0f}MB < {max_mb}MB")
            return False
        return True
    except Exception:
        return True


def cleanup_work_dir(task_id: str):
    """清理任务临时文件 — 修复 #12"""
    task_dir = os.path.join(WORK_DIR_BASE, task_id)
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)
        print(f"  🧹 清理临时目录: {task_dir}")

    # 清理进度文件
    prog_file = os.path.join(WORK_DIR_BASE, "progress", f"{task_id}.json")
    if os.path.exists(prog_file):
        os.remove(prog_file)


# ── 核心渲染函数 ──────────────────────────────────────────────

def render_page_to_video(page_image: str, audio_path: str, output_path: str,
                          duration: float = None):
    """将单页图片 + 语音 → 视频段

    修复 #4: 用 -loop 1 -i png 替代 YUV管道
    修复 #5: -loop 1 必须在 -i 之前
    修复 #6: 统一 MP3 编码
    """
    if not os.path.exists(page_image):
        print(f"  ❌ 图片不存在: {page_image}")
        return False

    has_audio = audio_path and os.path.exists(audio_path)

    if has_audio:
        # 有语音：用语音时长
        if duration is None:
            duration = tts_engine.get_audio_duration(audio_path)
        if duration <= 0:
            duration = 5.0

        # 修复 #4, #5: -loop 1 -i 顺序正确
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", page_image,
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "libmp3lame",     # 修复 #6: MP3 替代 AAC
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            "-shortest",
            output_path,
        ]
    else:
        # 无语音：固定时长
        if duration is None:
            duration = 4.0
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", page_image,
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            output_path,
        ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=120,  # 修复 #9: 单段编码最长 2 分钟
        )
        if result.returncode != 0:
            print(f"  ❌ ffmpeg 失败: {result.stderr[:200]}")
            return False
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print(f"  ❌ 输出为空文件: {output_path}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  ❌ ffmpeg 超时 (>{120}s)")
        return False
    except Exception as e:
        print(f"  ❌ ffmpeg 异常: {e}")
        return False


def concat_videos(video_segments: list, output_path: str) -> bool:
    """拼接多个视频段

    修复 #6: 确保输出也是 MP3 编码
    """
    if not video_segments:
        return False

    # 创建 concat 列表
    concat_dir = tempfile.mkdtemp()
    concat_file = os.path.join(concat_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for vf in video_segments:
            if os.path.exists(vf) and os.path.getsize(vf) > 0:
                f.write(f"file '{os.path.abspath(vf)}'\n")

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264",
            "-c:a", "libmp3lame",    # 修复 #6
            "-preset", "fast",
            "-crf", "23",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"  ❌ 拼接失败: {result.stderr[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  ❌ 拼接异常: {e}")
        return False
    finally:
        shutil.rmtree(concat_dir, ignore_errors=True)


# ── 生成流程 ──────────────────────────────────────────────────

def generate_video(doc_path: str,
                    task_id: str = None,
                    output_name: str = None,
                    template: str = "business",
                    voice: str = "yunxi",
                    page_duration: float = None,
                    tts_enabled: bool = True) -> dict:
    """完整的文档→视频生成流程

    Args:
        doc_path: 文档路径 (.pptx/.docx/.pdf/.jpg/...)
        task_id: 任务ID (用于进度追踪)
        output_name: 输出文件名 (默认自动生成)
        template: 模板 ("business"|"clean"|"minimal")
        voice: 语音 ("yunxi"|"xiaoxiao"|"yunyang"|"xiaochen")
        page_duration: 每页时长 (秒，默认自动/语音时长)
        tts_enabled: 是否生成语音

    Returns:
        {"success": bool, "output": str|None, "error": str|None}
    """
    start_time = time.time()
    task_id = task_id or f"video_{int(time.time())}"
    task_dir = os.path.join(WORK_DIR_BASE, task_id)
    os.makedirs(task_dir, exist_ok=True)

    reporter = ProgressReporter(task_id) if task_id else None

    # ── Step 0: 磁盘检查 ──
    if not check_disk_space("/tmp"):
        msg = "磁盘空间不足"
        if reporter: reporter.error(msg)
        return {"success": False, "output": None, "error": msg}

    # ── Step 1: 解析文档 ──
    print(f"\n{'='*60}")
    print(f"📄 解析文档: {doc_path}")
    print(f"{'='*60}")

    if reporter: reporter.parsing()

    if not os.path.exists(doc_path):
        msg = f"文件不存在: {doc_path}"
        if reporter: reporter.error(msg)
        return {"success": False, "output": None, "error": msg}

    try:
        doc = doc_parser.parse(doc_path)
    except Exception as e:
        msg = f"文档解析失败: {e}"
        if reporter: reporter.error(msg)
        return {"success": False, "output": None, "error": msg}

    pages = doc["pages"][:MAX_PAGES]  # 限制页数
    total_pages = len(pages)
    print(f"📊 共 {doc['total_pages']} 页，处理 {total_pages} 页")

    if total_pages == 0:
        msg = "文档为空"
        if reporter: reporter.error(msg)
        return {"success": False, "output": None, "error": msg}

    # ── Step 2: 渲染每页为图片 ──
    print(f"\n{'='*60}")
    print(f"🎨 渲染 {total_pages} 页")
    print(f"{'='*60}")

    rendered_images = []
    for i, page in enumerate(pages):
        if reporter: reporter.rendering(i + 1, total_pages)

        img_path = os.path.join(task_dir, f"page_{i:04d}.jpg")
        try:
            doc_parser.render_page_as_image(
                page, img_path,
                template=template,
            )
            if os.path.exists(img_path) and os.path.getsize(img_path) > 100:
                rendered_images.append(img_path)
                print(f"  ✅ 第{i+1}页: {page.get('title', '')[:30]}")
            else:
                print(f"  ⚠️ 第{i+1}页渲染文件无效")
        except Exception as e:
            print(f"  ⚠️ 第{i+1}页渲染失败: {e}")

    if not rendered_images:
        msg = "所有页面渲染失败"
        if reporter: reporter.error(msg)
        return {"success": False, "output": None, "error": msg}

    # ── Step 3: 生成语音 ──
    audio_segments = [None] * len(rendered_images)

    if tts_enabled and tts_engine.check_edge_tts():
        print(f"\n{'='*60}")
        print(f"🗣️ 生成语音 ({voice})")
        print(f"{'='*60}")

        for i, img_path in enumerate(rendered_images):
            if reporter: reporter.tts(i + 1, len(rendered_images))

            text = pages[i].get("text", "")
            if text.strip():
                audio_path = os.path.join(task_dir, f"speech_{i:04d}.mp3")  # 修复 #6
                ok = tts_engine.generate_speech(text, audio_path, voice=voice)
                if ok:
                    audio_segments[i] = audio_path
                    dur = tts_engine.get_audio_duration(audio_path)
                    print(f"  ✅ 语音{i+1}: {text[:30]}... ({dur:.1f}s)")
                else:
                    print(f"  ⚠️ 语音{i+1}: {text[:30]}... 失败")

    # ── Step 4: 编码视频段 ──
    print(f"\n{'='*60}")
    print(f"🎬 编码 {len(rendered_images)} 个视频段")
    print(f"{'='*60}")

    if reporter: reporter.encoding()

    video_segments = []
    for i, img_path in enumerate(rendered_images):
        seg_path = os.path.join(task_dir, f"seg_{i:04d}.mp4")
        audio_path = audio_segments[i] if i < len(audio_segments) else None
        dur = page_duration
        if dur is None and audio_path:
            dur = tts_engine.get_audio_duration(audio_path)
        if dur is None or dur <= 0:
            dur = 4.0

        ok = render_page_to_video(img_path, audio_path, seg_path, dur)
        if ok:
            video_segments.append(seg_path)
            print(f"  ✅ 段{i+1}: {dur:.1f}s")
        else:
            print(f"  ❌ 段{i+1} 编码失败")

    if not video_segments:
        msg = "所有视频段编码失败"
        if reporter: reporter.error(msg)
        cleanup_work_dir(task_id)
        return {"success": False, "output": None, "error": msg}

    # ── Step 5: 拼接 ──
    print(f"\n{'='*60}")
    print(f"🔗 拼接 {len(video_segments)} 个视频段")
    print(f"{'='*60}")

    output_name = output_name or f"{task_id}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    ok = concat_videos(video_segments, output_path)
    if not ok:
        msg = "视频拼接失败"
        if reporter: reporter.error(msg)
        cleanup_work_dir(task_id)
        return {"success": False, "output": None, "error": msg}

    # ── Step 6: 完成 ──
    elapsed = time.time() - start_time
    file_size = os.path.getsize(output_path)
    print(f"\n{'='*60}")
    print(f"✅ 视频生成完成!")
    print(f"📁 输出: {output_path}")
    print(f"📐 大小: {file_size / 1024 / 1024:.1f} MB")
    print(f"⏱️  耗时: {elapsed:.0f}s")
    print(f"📄 页数: {total_pages}")
    print(f"{'='*60}")

    result = {
        "success": True,
        "output": output_path,
        "task_id": task_id,
        "pages": total_pages,
        "duration_sec": round(elapsed, 1),
        "size_bytes": file_size,
        "size_mb": round(file_size / 1024 / 1024, 1),
    }

    if reporter: reporter.done(output_path)

    # 修复 #12: 清理临时文件
    cleanup_work_dir(task_id)

    return result


# ── CLI 入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="🎬 ComputeHub 视频生成引擎")
    parser.add_argument("--doc", required=True, help="文档路径 (.pptx/.docx/.pdf)")
    parser.add_argument("--output", help="输出文件名 (默认自动)")
    parser.add_argument("--task-id", help="任务ID")
    parser.add_argument("--template", default="business",
                        choices=["business", "clean", "minimal"],
                        help="渲染模板")
    parser.add_argument("--voice", default="yunxi",
                        choices=["yunxi", "xiaoxiao", "yunyang", "xiaochen"],
                        help="语音角色")
    parser.add_argument("--page-duration", type=float, default=None,
                        help="每页时长 (秒，默认自动/语音时长)")
    parser.add_argument("--no-tts", action="store_true", help="禁用语音")
    parser.add_argument("--progress", action="store_true", help="输出进度到 stdout JSON")

    args = parser.parse_args()

    result = generate_video(
        doc_path=args.doc,
        task_id=args.task_id,
        output_name=args.output,
        template=args.template,
        voice=args.voice,
        page_duration=args.page_duration,
        tts_enabled=not args.no_tts,
    )

    if args.progress:
        print(f"\nPROGRESS_JSON:{json.dumps(result, ensure_ascii=False)}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
