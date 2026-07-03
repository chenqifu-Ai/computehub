#!/usr/bin/env python3
"""
🎬 ComputeHub 视频生产管线
==========================
支持: 文字动画 / 图片合成 / 语音配音 / 多场景拼接 / 字幕叠加

用法:
  # 命令行直接生成
  python3 video_pipeline.py --scenes 3 --text "你好世界" --output /var/computehub/gallery/demo.mp4

  # 通过 ComputeHub 提交
  python3 submit_video_task.py --script "夏日海滩Vlog" --scenes 5 --duration 30
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import hashlib
import re
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────

OUTPUT_DIR = "/var/computehub/gallery"
FONT_DIRS = [
    "/system/fonts",           # Android
    "/usr/share/fonts",        # Linux
    "/usr/share/fonts/truetype",
]
DEFAULT_FONT = "MiSansVF.ttf"  # Android MiSans 中文字体
FALLBACK_FONT = "DroidSans.ttf"

# 场景模板
SCENE_TEMPLATES = {
    "title": {
        "desc": "开场标题 — 大字居中 + 背景动效",
        "ffmpeg": (
            "ffmpeg -y -f lavfi -i "
            "color=c={bg_color}:s={width}x{height}:d={duration}:r=30 "
            "-vf \""
            "drawtext=text='{text}':"
            "fontfile={font}:"
            "fontsize={fontsize}:"
            "fontcolor={fontcolor}:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            "shadowcolor=black:shadowx=2:shadowy=2"
            "\" "
            "{output}"
        )
    },
    "subtitle": {
        "desc": "底部字幕 — 下方文字",
        "ffmpeg": (
            "ffmpeg -y -f lavfi -i "
            "color=c={bg_color}:s={width}x{height}:d={duration}:r=30 "
            "-vf \""
            "drawtext=text='{text}':"
            "fontfile={font}:"
            "fontsize={fontsize}:"
            "fontcolor={fontcolor}:"
            "x=(w-text_w)/2:y=h-text_h-{margin}"
            "\" "
            "{output}"
        )
    },
    "image_slideshow": {
        "desc": "图片轮播 — 图片 + 文字叠加",
        "ffmpeg": (
            "ffmpeg -y -loop 1 -i {image} "
            "-c:v libx264 -t {duration} -pix_fmt yuv420p "
            "-vf \""
            "scale={width}:{height}:force_original_aspect_ratio=decrease,"
            "pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={bg_color},"
            "drawtext=text='{text}':"
            "fontfile={font}:"
            "fontsize={fontsize}:"
            "fontcolor={fontcolor}:"
            "x=(w-text_w)/2:y=h-text_h-{margin}"
            "\" "
            "{output}"
        )
    },
    "audio_visual": {
        "desc": "音频可视化 — 声波动画 + 封面图",
        "ffmpeg": (
            "ffmpeg -y -i {audio} "
            "-filter_complex \""
            "[0:a]showwaves=s={width}x{height}:mode=cline:rate=25:colors={wave_color}[v];"
            "[v]drawtext=text='{text}':"
            "fontfile={font}:"
            "fontsize={fontsize}:"
            "fontcolor={fontcolor}:"
            "x=(w-text_w)/2:y=20"
            "[out]"
            "\" "
            "-map \"[out]\" -map 0:a -c:v libx264 -preset fast -pix_fmt yuv420p "
            "{output}"
        )
    },
    "concat": {
        "desc": "视频拼接 — 多段合并",
        "ffmpeg": (
            "ffmpeg -y -f concat -safe 0 "
            "-i {concat_file} "
            "-c copy {output}"
        )
    },
}

# ── 工具函数 ──────────────────────────────────────────────────

def find_font():
    """找到最佳中文字体 — 按优先级: MiSansVF > MiSans* > DroidSans > Noto > 其他"""
    priority_patterns = [
        lambda n: 'misansvf' in n.lower() and n.endswith('.ttf'),    # 0: 最佳
        lambda n: 'misans' in n.lower() and 'japan' not in n.lower() 
                 and 'korean' not in n.lower() and 'latin' not in n.lower()
                 and n.endswith('.ttf'),                               # 1: 其他 MiSans 中文
        lambda n: 'droidsans' in n.lower() and n.endswith('.ttf'),    # 2: DroidSans
        lambda n: 'noto' in n.lower() and 'cj' in n.lower() and n.endswith('.ttf'),  # 3: Noto CJK
        lambda n: n.lower().endswith('.ttf'),                         # 4: 任意 ttf
    ]
    for font_dir in FONT_DIRS:
        if not os.path.isdir(font_dir):
            continue
        files = [f for f in os.listdir(font_dir) if f.lower().endswith(('.ttf', '.otf'))]
        for pattern in priority_patterns:
            matches = [f for f in files if pattern(f)]
            if matches:
                return os.path.join(font_dir, matches[0])
    return "/system/fonts/DroidSans.ttf"  # 硬 fallback


def safe_filename(text):
    """从文本生成安全的文件名"""
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', text)[:50]
    return safe or f"video_{int(time.time())}"


def run_cmd(cmd, desc=""):
    """执行命令并监控"""
    print(f"  🎬 {desc or '执行'}: {cmd[:120]}...")
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"  ❌ 失败 (exit={result.returncode}): {result.stderr[:200]}")
        return False, result.stderr
    print(f"  ✅ 完成 ({elapsed:.1f}s)")
    return True, result.stdout


def make_concat_file(video_files, concat_path):
    """生成 FFmpeg concat 文件列表"""
    with open(concat_path, 'w') as f:
        for vf in video_files:
            if os.path.exists(vf):
                f.write(f"file '{os.path.abspath(vf)}'\n")
    return concat_path


# ── 场景生成器 ────────────────────────────────────────────────

class Scene:
    """单个场景"""
    def __init__(self, template="title", **kwargs):
        self.template = template
        self.kwargs = kwargs

    def render(self, output_path, font=None):
        """渲染场景到视频文件"""
        if self.template not in SCENE_TEMPLATES:
            raise ValueError(f"未知模板: {self.template}")

        tmpl = SCENE_TEMPLATES[self.template]["ffmpeg"]
        kwargs = dict(self.kwargs)
        kwargs.setdefault("width", 1920)
        kwargs.setdefault("height", 1080)
        kwargs.setdefault("duration", 5)
        kwargs.setdefault("bg_color", "black")
        kwargs.setdefault("fontcolor", "white")
        kwargs.setdefault("fontsize", 60)
        kwargs.setdefault("text", "默认标题")
        kwargs.setdefault("margin", 80)
        kwargs.setdefault("wave_color", "white")
        kwargs.setdefault("font", font or find_font())
        kwargs["output"] = output_path

        cmd = tmpl.format(**kwargs)
        ok, _ = run_cmd(cmd, f"渲染场景 [{self.template}]: {kwargs.get('text','')[:30]}")
        return ok


# ── 视频制作管线 ──────────────────────────────────────────────

class VideoPipeline:
    """视频生产管线"""

    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = output_dir
        self.font = find_font()
        self.scenes = []
        self.work_dir = tempfile.mkdtemp(prefix="video_pipeline_")
        self.rendered_scenes = []
        self.final_output = None

        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 工作目录: {self.work_dir}")
        print(f"🔤 字体: {self.font}")

    def add_scene(self, template="title", **kwargs):
        """添加场景"""
        self.scenes.append(Scene(template, **kwargs))
        return self

    def add_title_scene(self, text, duration=5, bg_color="black", fontsize=80):
        """添加标题场景"""
        return self.add_scene("title", text=text, duration=duration,
                              bg_color=bg_color, fontsize=fontsize)

    def add_subtitle_scene(self, text, duration=4, bg_color="#1a1a2e", fontsize=50):
        """添加字幕场景"""
        return self.add_scene("subtitle", text=text, duration=duration,
                              bg_color=bg_color, fontsize=fontsize)

    def add_image_scene(self, image_path, text="", duration=5, bg_color="black"):
        """添加图片场景"""
        return self.add_scene("image_slideshow", image=image_path, text=text,
                              duration=duration, bg_color=bg_color)

    def add_audio_scene(self, audio_path, text="音频可视化", wave_color="#f7971e"):
        """添加音频可视化场景"""
        # 用音频时长
        dur = get_audio_duration(audio_path) or 30
        return self.add_scene("audio_visual", audio=audio_path, text=text,
                              wave_color=wave_color)

    def render_all(self):
        """渲染所有场景"""
        print(f"\n{'='*60}")
        print(f"🎬 开始渲染 {len(self.scenes)} 个场景")
        print(f"{'='*60}")

        self.rendered_scenes = []
        for i, scene in enumerate(self.scenes):
            out_path = os.path.join(self.work_dir, f"scene_{i:04d}.mp4")
            ok = scene.render(out_path)
            if ok:
                self.rendered_scenes.append(out_path)
            else:
                print(f"  ⚠️ 场景 {i} 渲染失败，跳过")

        print(f"\n✅ 成功渲染 {len(self.rendered_scenes)}/{len(self.scenes)} 个场景")
        return self.rendered_scenes

    def concat(self, output_filename=None):
        """拼接所有场景"""
        if not self.rendered_scenes:
            print("❌ 没有可拼接的场景")
            return None

        if output_filename is None:
            output_filename = f"video_{int(time.time())}.mp4"

        output_path = os.path.join(self.output_dir, output_filename)

        if len(self.rendered_scenes) == 1:
            # 只有一个场景，直接复制
            import shutil
            shutil.copy2(self.rendered_scenes[0], output_path)
            print(f"📦 单个场景，直接复制到: {output_path}")
        else:
            # 多个场景用 concat
            concat_file = os.path.join(self.work_dir, "concat_list.txt")
            make_concat_file(self.rendered_scenes, concat_file)

            cmd = (
                f"ffmpeg -y -f concat -safe 0 "
                f"-i {concat_file} "
                f"-c copy {output_path}"
            )
            ok, _ = run_cmd(cmd, "拼接所有场景")
            if not ok:
                # fallback: 重新编码
                cmd = (
                    f"ffmpeg -y -f concat -safe 0 "
                    f"-i {concat_file} "
                    f"-c:v libx264 -preset fast -crf 22 "
                    f"-c:a aac -b:a 128k {output_path}"
                )
                ok, _ = run_cmd(cmd, "重新编码拼接")
                if not ok:
                    print("❌ 拼接失败")
                    return None

        file_size = os.path.getsize(output_path)
        print(f"📦 输出: {output_path}")
        print(f"📐 大小: {file_size / 1024 / 1024:.1f} MB")
        self.final_output = output_path
        return output_path

    def add_audio_to_video(self, audio_path, output_filename=None):
        """给视频加背景音乐"""
        if not self.final_output or not os.path.exists(self.final_output):
            print("❌ 没有最终视频")
            return None

        if output_filename is None:
            output_filename = f"video_audio_{int(time.time())}.mp4"

        output_path = os.path.join(self.output_dir, output_filename)
        cmd = (
            f"ffmpeg -y -i {self.final_output} -i {audio_path} "
            f"-c:v copy -c:a aac -b:a 128k "
            f"-shortest {output_path}"
        )
        ok, _ = run_cmd(cmd, "添加背景音乐")
        if ok:
            self.final_output = output_path
        return output_path

    def add_subtitle_file(self, srt_path, output_filename=None):
        """叠加字幕文件"""
        if not self.final_output or not os.path.exists(self.final_output):
            print("❌ 没有最终视频")
            return None

        if output_filename is None:
            output_filename = f"video_sub_{int(time.time())}.mp4"

        output_path = os.path.join(self.output_dir, output_filename)
        cmd = (
            f"ffmpeg -y -i {self.final_output} "
            f"-vf \"subtitles={srt_path}\" "
            f"-c:a copy {output_path}"
        )
        ok, _ = run_cmd(cmd, "叠加字幕")
        if ok:
            self.final_output = output_path
        return output_path

    def generate_srt(self, lines, output_path=None):
        """生成 SRT 字幕文件"""
        if output_path is None:
            output_path = os.path.join(self.work_dir, "subtitle.srt")

        with open(output_path, 'w', encoding='utf-8') as f:
            idx = 1
            start = 0
            for line in lines:
                # 假设每行 3 秒
                end = start + 3
                f.write(f"{idx}\n")
                f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
                f.write(f"{line}\n\n")
                start = end
                idx += 1

        print(f"📝 SRT 字幕生成: {output_path} ({len(lines)} 行)")
        return output_path

    def cleanup(self):
        """清理临时文件"""
        import shutil
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
            print(f"🧹 清理临时目录: {self.work_dir}")

    def get_report(self):
        """获取生产报告"""
        if self.final_output and os.path.exists(self.final_output):
            size = os.path.getsize(self.final_output)
            return {
                "output": self.final_output,
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 1),
                "scenes_total": len(self.scenes),
                "scenes_rendered": len(self.rendered_scenes),
            }
        return {"error": "no output"}


def format_srt_time(seconds):
    """SRT 时间格式"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def get_audio_duration(audio_path):
    """获取音频时长"""
    if not os.path.exists(audio_path):
        return None
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{audio_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, TypeError):
        return None


# ── 快速制作用例 ──────────────────────────────────────────────

def quick_title_video(text, output_name=None, duration=10, bg_color="#302b63"):
    """快速生成标题视频"""
    pipe = VideoPipeline()
    pipe.add_title_scene(text, duration=duration, bg_color=bg_color)
    pipe.render_all()
    return pipe.concat(output_name)


def quick_slideshow(images, text_lines=None, duration_per=5):
    """快速生成图片轮播视频"""
    pipe = VideoPipeline()
    for i, img in enumerate(images):
        text = text_lines[i] if text_lines and i < len(text_lines) else ""
        if os.path.exists(img):
            pipe.add_image_scene(img, text=text, duration=duration_per)
    pipe.render_all()
    return pipe.concat()


def create_script_video(script_lines, output_name=None, bg_color="#1a1a2e"):
    """脚本转视频：每行一个字幕场景"""
    pipe = VideoPipeline()
    pipe.add_title_scene("🎬 " + script_lines[0] if script_lines else "小智影业",
                         bg_color=bg_color, duration=6)
    for line in script_lines[1:]:
        pipe.add_subtitle_scene(line, bg_color=bg_color, duration=4)
    pipe.render_all()
    return pipe.concat(output_name)


# ── 主入口 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="🎬 ComputeHub 视频生产管线")
    parser.add_argument("--script", type=str, help="脚本文件路径 (每行一个字幕)")
    parser.add_argument("--text", type=str, default="你好世界", help="标题文字")
    parser.add_argument("--scenes", type=int, default=3, help="字幕场景数")
    parser.add_argument("--duration", type=int, default=5, help="每段时长(秒)")
    parser.add_argument("--output", type=str, help="输出文件名")
    parser.add_argument("--bg", type=str, default="#302b63", help="背景色")
    parser.add_argument("--mode", type=str, default="script",
                        choices=["title", "script", "slideshow"],
                        help="模式: title=单标题, script=脚本转视频, slideshow=图片轮播")
    parser.add_argument("--images", type=str, nargs="*",
                        help="图片路径 (slideshow 模式)")
    parser.add_argument("--audio", type=str, help="背景音乐或配音路径")
    parser.add_argument("--submit", action="store_true",
                        help="通过 ComputeHub 提交任务")
    parser.add_argument("--gw", type=str, default="http://localhost:8282",
                        help="Gateway 地址")

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🎬 小智影业 · 视频生产线")
    print(f"{'='*60}\n")

    output_name = args.output or f"{safe_filename(args.text or 'video')}_{int(time.time())}.mp4"

    if args.script and os.path.exists(args.script):
        # 从文件读取脚本
        with open(args.script, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
        pipe = VideoPipeline()
        pipe.add_title_scene("🎬 " + lines[0] if lines else "小智影业",
                             bg_color=args.bg)
        for line in lines[1:]:
            pipe.add_subtitle_scene(line, bg_color=args.bg, duration=args.duration)
        pipe.render_all()
        pipe.concat(output_name)

    elif args.mode == "title":
        pipe = VideoPipeline()
        pipe.add_title_scene(args.text, duration=args.duration * args.scenes,
                             bg_color=args.bg)
        pipe.render_all()
        pipe.concat(output_name)

    elif args.mode == "script":
        # 从文本生成多字幕场景
        sentences = [s.strip() for s in args.text.replace('。', '\n').replace('！', '\n').replace('？', '\n').split('\n') if s.strip()]
        if not sentences:
            sentences = [args.text]
        pipe = VideoPipeline()
        pipe.add_title_scene("🎬 " + sentences[0], bg_color=args.bg)
        for s in sentences[1:]:
            pipe.add_subtitle_scene(s, bg_color=args.bg, duration=args.duration)
        pipe.render_all()
        pipe.concat(output_name)

    elif args.mode == "slideshow" and args.images:
        pipe = VideoPipeline()
        for img in args.images:
            if os.path.exists(img):
                pipe.add_image_scene(img, duration=args.duration)
        pipe.render_all()
        pipe.concat(output_name)

    # 加背景音乐
    if args.audio and os.path.exists(args.audio):
        pipe.add_audio_to_video(args.audio)

    report = pipe.get_report()
    print(f"\n{'='*60}")
    print(f"📊 生产报告:")
    print(f"  输出: {report.get('output', 'N/A')}")
    print(f"  大小: {report.get('size_mb', 'N/A')} MB")
    print(f"  场景: {report.get('scenes_rendered', 0)}/{report.get('scenes_total', 0)}")
    print(f"{'='*60}")

    pipe.cleanup()

    # 提交到 ComputeHub
    if args.submit:
        if report.get('output') and os.path.exists(report['output']):
            print(f"\n📤 文件已在 Gallery 中: {report['output']}")
        else:
            print(f"\n⚠️  没有生成输出，跳过提交")

    return report


if __name__ == "__main__":
    main()
