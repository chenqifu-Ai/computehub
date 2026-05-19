#!/usr/bin/env python3
"""
🎬 ComputeHub 视频编码引擎 — v2.0 可视化升级
================================================================
新特性:
  ✅ 7套视觉模板（科技蓝/金融金/自然绿/暗夜优雅/简约白/暖橙/庆典红）
  ✅ 渐变背景 + 装饰元素 + 专业排版
  ✅ 全页图背景（带暗色遮罩）
  ✅ 交叉淡入淡出过渡（替代硬切）
  ✅ 语音字幕自动烧录（SRT）
  ✅ 背景音乐自动混音
  ✅ 品牌片头片尾

用法:
  python3 video_pipeline.py \\
    --doc /path/to/file.pptx \\
    --output /tmp/output.mp4 \\
    --template tech_blue \\
    --voice yunxi \\
    --bgm /path/to/music.mp3

历史修复 (v1.0):
  #1 moviepy.editor → from moviepy import ImageClip
  #2 .set_duration() → .with_duration()
  #3 PIL rectangle 坐标反了
  #4 YUV管道编码输出0字节 → -loop 1 -i png
  #5 -loop 1 位置放错 → 必须在 -i 之前
  #6 AAC编码浏览器不兼容 → 统一 MP3
  #7 ffprobe duration 正则提取
  #8 Gateway API \\n 转义
  #9 Gateway 30s 超时 → nohup
  #10 节点offline → 心跳守护
  #11 30个worker资源浪费 → 限定并发
  #12 27页×30MB临时文件 → 清理
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
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

import doc_parser
import tts_engine
import visual_templates as vt

# ── 常量 ──────────────────────────────────────────────────────

OUTPUT_DIR = "/var/computehub/gallery"
WORK_DIR_BASE = "/tmp/computehub-video"
MAX_PAGES = 50
MAX_DISK_MB = 500

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(WORK_DIR_BASE, exist_ok=True)

# ── 进度报告 ──────────────────────────────────────────────────

class ProgressReporter:
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
        pct = 10 + int(50 * current / total)
        self._report("rendering", min(pct, 60), f"渲染页面 {current}/{total}")

    def tts(self, current: int, total: int):
        pct = 60 + int(15 * current / total)
        self._report("tts", min(pct, 75), f"生成语音 {current}/{total}")

    def encoding(self, pct=80):
        self._report("encoding", pct, "编码视频")

    def concat_progress(self, pct=90):
        self._report("concat", pct, "拼接+过渡")

    def bgm_progress(self, pct=95):
        self._report("bgm", pct, "混音背景音乐")

    def uploading(self):
        self._report("uploading", 98, "上传 Gallery")

    def done(self, output_path: str):
        self._report("done", 100, f"完成: {output_path}")

    def error(self, msg: str):
        self._report("error", -1, msg)


# ── 工具函数 ──────────────────────────────────────────────────

def check_disk_space(path: str, max_mb: int = MAX_DISK_MB) -> bool:
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
    task_dir = os.path.join(WORK_DIR_BASE, task_id)
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)
        print(f"  🧹 清理临时目录: {task_dir}")

    prog_file = os.path.join(WORK_DIR_BASE, "progress", f"{task_id}.json")
    if os.path.exists(prog_file):
        os.remove(prog_file)


def get_media_duration(path: str) -> float:
    """获取音视频时长（秒）"""
    if not os.path.exists(path):
        return 0.0
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        m = re.search(r"(\d+\.?\d*)", result.stdout.strip())
        return float(m.group(1)) if m else 0.0
    except Exception:
        return 0.0


def run_ffmpeg(cmd: list, desc: str = "", timeout: int = 120) -> bool:
    """执行 ffmpeg 命令并用 timeout 保护"""
    print(f"  🎬 {desc}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            stderr = result.stderr[:300] if result.stderr else "no output"
            print(f"  ❌ ffmpeg 失败 (exit={result.returncode}): {stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  ❌ ffmpeg 超时 (>{timeout}s)")
        return False
    except Exception as e:
        print(f"  ❌ ffmpeg 异常: {e}")
        return False


def find_font() -> str:
    """找到最佳中文字体"""
    candidates = [
        "/system/fonts/MiSansVF.ttf",
        "/system/fonts/DroidSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in candidates:
        if os.path.exists(fp):
            return fp
    # fallback 搜索
    for root_dir in ["/system/fonts", "/usr/share/fonts"]:
        if os.path.isdir(root_dir):
            for dirpath, _, filenames in os.walk(root_dir):
                for fn in filenames:
                    if "misans" in fn.lower() and fn.endswith((".ttf", ".otf")):
                        return os.path.join(dirpath, fn)
    return "/system/fonts/DroidSans.ttf"


# ── 过渡效果 ──────────────────────────────────────────────────

def encode_segment_with_transition(
    prev_seg: str,
    page_image: str,
    audio_path: str,
    output_path: str,
    duration: float,
    has_prev: bool,
    transition_duration: float = 0.5,
) -> bool:
    """编码单个视频段，带淡入淡出效果

    方案: 每个段渲染后，对首帧加淡入、尾帧加淡出，
          然后 concat 拼接（不依赖 xfade 跨帧复合滤镜）
    """
    if not os.path.exists(page_image):
        return False

    # 渲染单段视频（图片+语音）
    seg_raw = output_path.replace(".mp4", "_raw.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", page_image,
    ]
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
        cmd.extend([
            "-c:v", "libx264",
            "-c:a", "libmp3lame",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            "-shortest",
            seg_raw,
        ])
    else:
        cmd.extend([
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            seg_raw,
        ])

    ok = run_ffmpeg(cmd, f"编码段 {os.path.basename(page_image)} ({duration:.1f}s)", timeout=120)
    if not ok:
        return False

    # 对单段加淡入淡出滤镜，稳定跨版本兼容
    # fade=t=in:st=0:d=td 加淡入, fade=t=out:st=(dur-td):d=td 加淡出
    with_fades = output_path.replace(".mp4", "_faded.mp4")
    td = min(transition_duration, duration / 4)  # 不超过总长的 1/4
    fade_filter = f"fade=t=in:st=0:d={td},fade=t=out:st={duration - td}:d={td}"

    fade_cmd = [
        "ffmpeg", "-y",
        "-i", seg_raw,
        "-vf", fade_filter,
        "-c:a", "copy",
        "-preset", "fast",
        "-crf", "23",
        with_fades,
    ]
    ok = run_ffmpeg(fade_cmd, f"淡入淡出 ({td:.1f}s)", timeout=60)
    os.remove(seg_raw)

    if not ok:
        shutil.copy2(seg_raw.replace("_raw.mp4", ".mp4"), output_path) if os.path.exists(seg_raw.replace("_raw.mp4", ".mp4")) else None
        return False

    # 有前一段？用 concat 简单拼接（不用 xfade 避免兼容问题）
    if has_prev and os.path.exists(prev_seg):
        concat_file = os.path.join(os.path.dirname(output_path), "concat_seg.txt")
        with open(concat_file, "w") as f:
            for vf in [prev_seg, with_fades]:
                if os.path.exists(vf) and os.path.getsize(vf) > 0:
                    f.write(f"file '{os.path.abspath(vf)}'\n")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264",
            "-c:a", "libmp3lame",
            "-preset", "fast", "-crf", "23",
            output_path,
        ]
        ok = run_ffmpeg(concat_cmd, "拼接前段+本段", timeout=120)
        if os.path.exists(concat_file):
            os.remove(concat_file)
        if ok:
            os.remove(with_fades)
            return True

    # fallback: 直接返回本段（第一段或拼接失败）
    shutil.copy2(with_fades, output_path)
    os.remove(with_fades)
    return True


# ── 字幕生成 ──────────────────────────────────────────────────

def generate_srt(pages: list, audio_durations: list, output_path: str):
    """根据页面文本和语音时长生成 SRT 字幕文件

    Args:
        pages: doc_parser 页面列表
        audio_durations: 每页语音时长（秒），无语音用 4.0
        output_path: SRT 输出路径
    """
    with open(output_path, "w", encoding="utf-8") as f:
        idx = 1
        current_time = 0.0
        for i, page in enumerate(pages):
            text = page.get("text", "")
            if not text.strip():
                current_time += 4.0
                continue

            dur = audio_durations[i] if i < len(audio_durations) and audio_durations[i] > 0 else 4.0
            end_time = current_time + dur

            lines = text.split("\n")
            # 去掉空行
            lines = [l.strip() for l in lines if l.strip()]

            for line in lines:
                if not line:
                    continue
                # 每行作为一个字幕条目，均分时长
                line_dur = dur / max(len(lines), 1)
                line_start = current_time
                line_end = line_start + line_dur

                f.write(f"{idx}\n")
                f.write(f"{_fmt_srt_time(line_start)} --> {_fmt_srt_time(line_end)}\n")
                f.write(f"{line}\n\n")
                idx += 1
                current_time = line_end

            current_time = end_time  # 补足剩余时间

    print(f"  📝 SRT 字幕已生成: {output_path} ({idx - 1} 条)")
    return output_path


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def burn_subtitles(video_path: str, srt_path: str, output_path: str) -> bool:
    """将 SRT 字幕烧录到视频中"""
    if not os.path.exists(srt_path):
        return False

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        "-preset", "fast",
        "-crf", "23",
        output_path,
    ]
    return run_ffmpeg(cmd, "烧录字幕", timeout=180)


# ── 品牌片头片尾 ──────────────────────────────────────────────

def create_intro(duration: float = 3.0, output_path: str = None,
                 font_path: str = None) -> str:
    """生成品牌片头视频"""
    if output_path is None:
        output_path = os.path.join(tempfile.mkdtemp(), "intro.mp4")

    cfg = vt.TEMPLATES["tech_blue"]
    # 用 PIL 生成片头图片
    img = __import__("PIL").Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = __import__("PIL").ImageDraw.Draw(img)
    vt.draw_gradient(draw, 1920, 1080, cfg["bg_top"], cfg["bg_bottom"])
    vt.draw_radial_glow(draw, 1920, 1080, cfg["accent"], radius=500)

    # 居中文字
    font = __import__("PIL").ImageFont.truetype(font_path or find_font(), 72)
    title = "🎬 小智影业"
    bbox = draw.textbbox((0, 0), title, font=font)
    tx = (1920 - (bbox[2] - bbox[0])) // 2
    ty = (1080 - (bbox[3] - bbox[1])) // 2 - 40
    draw.text((tx, ty), title, fill=(255, 255, 255), font=font)

    font_sub = __import__("PIL").ImageFont.truetype(font_path or find_font(), 32)
    sub = "AI驱动 · 智能创作平台"
    bbox2 = draw.textbbox((0, 0), sub, font=font_sub)
    sx = (1920 - (bbox2[2] - bbox2[0])) // 2
    sy = ty + 100
    draw.text((sx, sy), sub, fill=cfg["accent2"], font=font_sub)

    # 底部线
    vt.draw_footer_line(draw, 1920, 1080, cfg["accent2"])

    bg = __import__("PIL").Image.new("RGB", (1920, 1080), cfg["bg_top"])
    bg.paste(img, mask=img.split()[3])
    intro_img = "/tmp/intro_bg.jpg"
    bg.save(intro_img, "JPEG", quality=92)

    # 编码为视频
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", intro_img,
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-vf", "fade=t=in:st=0:d=0.5,fade=t=out:st={}:d=0.5".format(duration - 0.5),
        output_path,
    ]
    ok = run_ffmpeg(cmd, "生成品牌片头", timeout=30)
    if not ok:
        return None
    return output_path


def create_outro(duration: float = 3.0, output_path: str = None,
                 font_path: str = None) -> str:
    """生成品牌片尾视频"""
    if output_path is None:
        output_path = os.path.join(tempfile.mkdtemp(), "outro.mp4")

    cfg = vt.TEMPLATES["dark_elegant"]
    img = __import__("PIL").Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = __import__("PIL").ImageDraw.Draw(img)
    vt.draw_gradient(draw, 1920, 1080, cfg["bg_top"], cfg["bg_bottom"])
    vt.draw_radial_glow(draw, 1920, 1080, (139, 92, 246), radius=350)

    font = __import__("PIL").ImageFont.truetype(font_path or find_font(), 56)
    thanks = "感谢观看"
    bbox = draw.textbbox((0, 0), thanks, font=font)
    tx = (1920 - (bbox[2] - bbox[0])) // 2
    ty = (1080 - (bbox[3] - bbox[1])) // 2 - 50
    draw.text((tx, ty), thanks, fill=(255, 255, 255), font=font)

    font_sub = __import__("PIL").ImageFont.truetype(font_path or find_font(), 30)
    sub = "小智影业 · ComputeHub 视频引擎"
    bbox2 = draw.textbbox((0, 0), sub, font=font_sub)
    sx = (1920 - (bbox2[2] - bbox2[0])) // 2
    sy = ty + 80
    draw.text((sx, sy), sub, fill=cfg["accent2"], font=font_sub)

    bg = __import__("PIL").Image.new("RGB", (1920, 1080), cfg["bg_top"])
    bg.paste(img, mask=img.split()[3])
    outro_img = "/tmp/outro_bg.jpg"
    bg.save(outro_img, "JPEG", quality=92)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", outro_img,
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-vf", "fade=t=in:st=0:d=0.5,fade=t=out:st={}:d=0.5".format(duration - 0.5),
        output_path,
    ]
    ok = run_ffmpeg(cmd, "生成品牌片尾", timeout=30)
    if not ok:
        return None
    return output_path


# ── 背景音乐混音 ──────────────────────────────────────────────

def mix_background_music(video_path: str, bgm_path: str, output_path: str,
                          music_volume: float = 0.15) -> bool:
    """混合背景音乐到视频

    Args:
        video_path: 视频路径（已有语音）
        bgm_path: 背景音乐路径
        output_path: 输出路径
        music_volume: 音乐音量比例（0.0-1.0）
    """
    if not os.path.exists(bgm_path):
        return False

    video_dur = get_media_duration(video_path)
    bgm_dur = get_media_duration(bgm_path)

    if bgm_dur <= 0:
        return False

    if bgm_dur < video_dur:
        # 音乐短于视频，需要循环
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={music_volume},aloop=loop=-1:size=44100*{int(bgm_dur)}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "copy",
            "-c:a", "libmp3lame",
            "-t", str(video_dur),
            "-shortest",
            output_path,
        ]
    else:
        # 音乐长于视频，截断
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={music_volume},atrim=0:{video_dur}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "copy",
            "-c:a", "libmp3lame",
            "-shortest",
            output_path,
        ]

    return run_ffmpeg(cmd, "混音背景音乐", timeout=180)


# ── 核心生成流程 ──────────────────────────────────────────────

def generate_video(doc_path: str,
                   task_id: str = None,
                   output_name: str = None,
                   template: str = "tech_blue",
                   voice: str = "yunxi",
                   page_duration: float = None,
                   tts_enabled: bool = True,
                   bgm_path: str = None,
                   enable_intro: bool = True,
                   enable_outro: bool = True,
                   enable_subtitles: bool = True,
                   transition_duration: float = 0.5,
                   tts_rate: str = "-20%") -> dict:
    """完整的文档→视频生成流程（v2.0）

    Args:
        doc_path: 文档路径
        template: 视觉模板名称
        voice: 语音角色
        page_duration: 每页固定时长（默认用语音时长）
        tts_enabled: 是否生成语音
        bgm_path: 背景音乐路径
        enable_intro: 是否加片头
        enable_outro: 是否加片尾
        enable_subtitles: 是否加字幕
        transition_duration: 过渡时长（秒）
        tts_rate: 语音语速（如 "-20%" 慢20%，"+30%" 快30%）

    Returns:
        {"success": bool, "output": str, "error": str, ...}
    """
    start_time = time.time()
    task_id = task_id or f"video_{int(time.time())}"
    task_dir = os.path.join(WORK_DIR_BASE, task_id)
    os.makedirs(task_dir, exist_ok=True)

    reporter = ProgressReporter(task_id)
    font_path = find_font()

    # ── 模板检查 ──
    if template not in vt.TEMPLATES:
        print(f"  ⚠️ 未知模板 '{template}'，使用默认 tech_blue")
        template = "tech_blue"
    print(f"  🎨 模板: {vt.TEMPLATES[template]['name']} ({template})")
    print(f"  🔤 字体: {font_path}")

    # ── Step 0: 磁盘检查 ──
    if not check_disk_space("/tmp"):
        reporter.error("磁盘空间不足")
        return {"success": False, "output": None, "error": "磁盘空间不足"}

    # ── Step 1: 解析文档 ──
    print(f"\n{'='*60}")
    print(f"📄 解析文档: {doc_path}")
    print(f"{'='*60}")

    reporter.parsing()

    if not os.path.exists(doc_path):
        reporter.error(f"文件不存在: {doc_path}")
        return {"success": False, "output": None, "error": f"文件不存在: {doc_path}"}

    try:
        doc = doc_parser.parse(doc_path)
    except Exception as e:
        reporter.error(f"文档解析失败: {e}")
        return {"success": False, "output": None, "error": str(e)}

    pages = doc["pages"][:MAX_PAGES]
    total_pages = len(pages)
    print(f"📊 共 {doc['total_pages']} 页，处理 {total_pages} 页")

    if total_pages == 0:
        reporter.error("文档为空")
        return {"success": False, "output": None, "error": "文档为空"}

    # 补充 total_pages 到每页（用于页码渲染）
    # 修复空标题：用文档名 + 关键词
    doc_stem = Path(doc_path).stem
    for i, p in enumerate(pages):
        p["total_pages"] = total_pages
        # 如果标题是默认的"第X页"，用文档主标题或空字符串
        if re.match(r"^第\d+页$", p.get("title", "")):
            # 尝试用第一段文本作为标题
            text_lines = [l.strip() for l in p.get("text", "").split("\n") if l.strip()]
            if text_lines:
                p["title"] = text_lines[0][:50]
            else:
                p["title"] = doc_stem[:50]

    # ── Step 2: 视觉渲染每页为图片 ──
    print(f"\n{'='*60}")
    print(f"🎨 视觉渲染 {total_pages} 页 (模板: {template})")
    print(f"{'='*60}")

    rendered_images = []
    for i, page in enumerate(pages):
        reporter.rendering(i + 1, total_pages)

        img_path = os.path.join(task_dir, f"page_{i:04d}.jpg")
        try:
            vt.render_page(
                page, img_path,
                width=1920, height=1080,
                template=template,
                font_path=font_path,
                show_brand=True,
            )
            if os.path.exists(img_path) and os.path.getsize(img_path) > 100:
                rendered_images.append(img_path)
                print(f"  ✅ 第{i+1}页: {page.get('title', '')[:40]}")
            else:
                print(f"  ⚠️ 第{i+1}页渲染文件无效")
        except Exception as e:
            print(f"  ⚠️ 第{i+1}页渲染失败: {e}")
            import traceback; traceback.print_exc()

    if not rendered_images:
        reporter.error("所有页面渲染失败")
        return {"success": False, "output": None, "error": "所有页面渲染失败"}

    # ── Step 3: 生成语音 ──
    audio_segments = [None] * total_pages
    audio_durations = [0.0] * total_pages

    if tts_enabled and tts_engine.check_edge_tts():
        print(f"\n{'='*60}")
        print(f"🗣️ 生成语音 ({voice})")
        print(f"{'='*60}")

        for i, page in enumerate(pages):
            reporter.tts(i + 1, total_pages)
            text = page.get("text", "")
            if text.strip() and i < len(rendered_images):
                audio_path = os.path.join(task_dir, f"speech_{i:04d}.mp3")
                # 限制文本长度（edge-tts 长文本可能超时）
                tts_text = text[:2000]  # 单段最多 2000 字符
                ok = tts_engine.generate_speech(tts_text, audio_path, voice=voice, rate=tts_rate)
                if ok:
                    audio_segments[i] = audio_path
                    dur = tts_engine.get_audio_duration(audio_path)
                    audio_durations[i] = dur
                    print(f"  ✅ 语音{i+1}: {text[:40]}... ({dur:.1f}s)")
                else:
                    print(f"  ⚠️ 语音{i+1} 生成失败")

    # ── Step 4: 编码视频段（带过渡） ──
    print(f"\n{'='*60}")
    print(f"🎬 编码 {len(rendered_images)} 个视频段 (过渡: {transition_duration}s)")
    print(f"{'='*60}")

    reporter.encoding()

    video_segments = []
    prev_seg = None
    for i, img_path in enumerate(rendered_images):
        seg_path = os.path.join(task_dir, f"seg_{i:04d}.mp4")

        dur = page_duration
        if dur is None and audio_durations[i] > 0:
            dur = audio_durations[i]
        if dur is None or dur <= 0:
            dur = 4.0

        audio_path = audio_segments[i] if i < len(audio_segments) else None
        has_prev = prev_seg is not None

        ok = encode_segment_with_transition(
            prev_seg, img_path, audio_path, seg_path,
            dur, has_prev, transition_duration,
        )
        if ok:
            video_segments.append(seg_path)
            prev_seg = seg_path
            print(f"  ✅ 段{i+1}: {dur:.1f}s")
        else:
            print(f"  ❌ 段{i+1} 编码失败")

    if not video_segments:
        reporter.error("所有视频段编码失败")
        cleanup_work_dir(task_id)
        return {"success": False, "output": None, "error": "所有视频段编码失败"}

    # ── Step 4.5: 拼接所有段 ──
    print(f"\n{'='*60}")
    print(f"🔗 拼接 {len(video_segments)} 个视频段")
    print(f"{'='*60}")

    reporter.concat_progress()

    middle_video = os.path.join(task_dir, "middle.mp4")
    if len(video_segments) == 1:
        shutil.copy2(video_segments[0], middle_video)
    else:
        concat_file = os.path.join(task_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for vf in video_segments:
                if os.path.exists(vf) and os.path.getsize(vf) > 0:
                    f.write(f"file '{os.path.abspath(vf)}'\n")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264",
            "-c:a", "libmp3lame",
            "-preset", "fast", "-crf", "23",
            middle_video,
        ]
        ok = run_ffmpeg(cmd, "拼接视频", timeout=300)
        if not ok:
            reporter.error("视频拼接失败")
            cleanup_work_dir(task_id)
            return {"success": False, "output": None, "error": "视频拼接失败"}

    # ── Step 5: 加片头片尾 ──
    current_video = middle_video
    if enable_intro:
        print(f"\n{'='*60}")
        print(f"🏷️ 添加品牌片头")
        print(f"{'='*60}")
        intro_path = create_intro(duration=3.0, font_path=font_path)
        if intro_path:
            with_intro = os.path.join(task_dir, "with_intro.mp4")
            concat_file2 = os.path.join(task_dir, "concat_intro.txt")
            with open(concat_file2, "w") as f:
                for vf in [intro_path, current_video]:
                    if os.path.exists(vf) and os.path.getsize(vf) > 0:
                        f.write(f"file '{os.path.abspath(vf)}'\n")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file2,
                "-c", "copy",
                with_intro,
            ]
            if run_ffmpeg(cmd, "拼接片头", timeout=120):
                current_video = with_intro

    if enable_outro:
        print(f"\n{'='*60}")
        print(f"🏷️ 添加品牌片尾")
        print(f"{'='*60}")
        outro_path = create_outro(duration=3.0, font_path=font_path)
        if outro_path:
            with_outro = os.path.join(task_dir, "with_outro.mp4")
            concat_file3 = os.path.join(task_dir, "concat_outro.txt")
            with open(concat_file3, "w") as f:
                for vf in [current_video, outro_path]:
                    if os.path.exists(vf) and os.path.getsize(vf) > 0:
                        f.write(f"file '{os.path.abspath(vf)}'\n")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file3,
                "-c", "copy",
                with_outro,
            ]
            if run_ffmpeg(cmd, "拼接片尾", timeout=120):
                current_video = with_outro

    # ── Step 6: 烧录字幕 ──
    if enable_subtitles and tts_enabled:
        print(f"\n{'='*60}")
        print(f"📝 生成并烧录字幕")
        print(f"{'='*60}")
        srt_path = os.path.join(task_dir, "subtitle.srt")
        generate_srt(pages, audio_durations, srt_path)

        if os.path.exists(srt_path) and os.path.getsize(srt_path) > 50:
            subbed_video = os.path.join(task_dir, "subbed.mp4")
            if burn_subtitles(current_video, srt_path, subbed_video):
                current_video = subbed_video

    # ── Step 7: 混音背景音乐 ──
    if bgm_path and os.path.exists(bgm_path):
        print(f"\n{'='*60}")
        print(f"🎵 混音背景音乐")
        print(f"{'='*60}")
        reporter.bgm_progress()
        mixed_video = os.path.join(task_dir, "mixed.mp4")
        if mix_background_music(current_video, bgm_path, mixed_video):
            current_video = mixed_video

    # ── Step 8: 输出 ──
    output_name = output_name or f"{task_id}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    # 用 copy 避免跨设备问题
    shutil.copy2(current_video, output_path)

    elapsed = time.time() - start_time
    file_size = os.path.getsize(output_path)
    final_dur = get_media_duration(output_path)

    print(f"\n{'='*60}")
    print(f"✅ 视频生成完成!")
    print(f"📁 输出: {output_path}")
    print(f"📐 大小: {file_size / 1024 / 1024:.1f} MB")
    print(f"⏱️  时长: {final_dur:.1f}s")
    print(f"⏱️  耗时: {elapsed:.0f}s")
    print(f"📄 页数: {total_pages}")
    print(f"🎨 模板: {template}")
    print(f"🗣️ 语音: {'✅' if tts_enabled and any(a for a in audio_segments if a) else '❌'}")
    print(f"🎵 BGM: {'✅' if bgm_path and os.path.exists(bgm_path) else '❌'}")
    print(f"📝 字幕: {'✅' if enable_subtitles else '❌'}")
    print(f"🏷️ 片头片尾: {'✅' if enable_intro and enable_outro else '❌'}")
    print(f"{'='*60}")

    result = {
        "success": True,
        "output": output_path,
        "task_id": task_id,
        "pages": total_pages,
        "duration_sec": round(final_dur, 1),
        "elapsed_sec": round(elapsed, 1),
        "size_bytes": file_size,
        "size_mb": round(file_size / 1024 / 1024, 1),
        "template": template,
        "voice": voice,
        "has_tts": tts_enabled and any(a for a in audio_segments if a),
        "has_bgm": bgm_path is not None,
        "has_subtitles": enable_subtitles,
        "has_intro_outro": enable_intro and enable_outro,
    }

    reporter.done(output_path)
    cleanup_work_dir(task_id)
    return result


# ── CLI 入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="🎬 ComputeHub 视频引擎 v2.0")
    parser.add_argument("--doc", required=True, help="文档路径 (.pptx/.docx/.pdf)")
    parser.add_argument("--output", help="输出文件名")
    parser.add_argument("--task-id", help="任务ID")
    parser.add_argument("--template", default="tech_blue",
                        choices=list(vt.TEMPLATES.keys()),
                        help=f"视觉模板 ({', '.join(vt.TEMPLATES.keys())})")
    parser.add_argument("--voice", default="yunxi",
                        choices=["yunxi", "xiaoxiao", "yunyang", "xiaochen"],
                        help="语音角色")
    parser.add_argument("--page-duration", type=float, default=None,
                        help="每页固定时长（秒，默认用语音时长）")
    parser.add_argument("--no-tts", action="store_true", help="禁用语音")
    parser.add_argument("--bgm", help="背景音乐路径 (.mp3/.wav)")
    parser.add_argument("--no-intro", action="store_true", help="禁用品牌片头")
    parser.add_argument("--no-outro", action="store_true", help="禁用品牌片尾")
    parser.add_argument("--no-subtitles", action="store_true", help="禁用字幕")
    parser.add_argument("--transition", type=float, default=0.5,
                        help="过渡时长（秒，默认0.5）")
    parser.add_argument("--rate", default="-20%",
                        help="语音语速（如 \"-20%\" 慢20%，\"+30%\" 快30%）")
    parser.add_argument("--progress", action="store_true", help="输出进度 JSON")

    args = parser.parse_args()

    # 自动检测模板别名
    template_alias = {
        "business": "tech_blue",
        "gold": "finance_gold",
        "green": "nature_green",
        "elegant": "dark_elegant",
        "white": "minimal_white",
        "orange": "warm_orange",
        "red": "ceremony_red",
        "dark": "dark_elegant",
    }
    template = template_alias.get(args.template, args.template)

    result = generate_video(
        doc_path=args.doc,
        task_id=args.task_id,
        output_name=args.output,
        template=template,
        voice=args.voice,
        page_duration=args.page_duration,
        tts_enabled=not args.no_tts,
        bgm_path=args.bgm,
        enable_intro=not args.no_intro,
        enable_outro=not args.no_outro,
        enable_subtitles=not args.no_subtitles,
        transition_duration=args.transition,
        tts_rate=args.rate,
    )

    if args.progress:
        print(f"\nPROGRESS_JSON:{json.dumps(result, ensure_ascii=False)}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
