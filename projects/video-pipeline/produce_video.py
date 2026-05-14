#!/usr/bin/env python3
"""
ComputeHub 视频生产线 - 短视频自动生产线
=======================================
输入: 主题 + 文案 → 自动生成短视频
工作流: gTTS(配音) → ffmpeg(合成视频)

用法:
  python3 produce_video.py --topic "AI改变生活" --output /tmp/output.mp4
  python3 produce_video.py --topic "今日股市" --duration 30 --style finance
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

try:
    from gtts import gTTS
except ImportError:
    print("❌ 需要 gTTS: pip install gtts")
    sys.exit(1)


# ====== 预设风格 ======
STYLES = {
    "default": {
        "bg_color": "black",
        "text_color": "white",
        "font_size": 36,
        "width": 720,
        "height": 1280,
        "fps": 24,
        "line_chars": 12,  # 每行字数
    },
    "finance": {
        "bg_color": "darkblue",
        "text_color": "gold",
        "font_size": 40,
        "width": 720,
        "height": 1280,
        "fps": 24,
        "line_chars": 14,
    },
    "tech": {
        "bg_color": "#1a1a2e",
        "text_color": "#00ff88",
        "font_size": 38,
        "width": 720,
        "height": 1280,
        "fps": 30,
        "line_chars": 13,
    },
    "news": {
        "bg_color": "#2c3e50",
        "text_color": "#ecf0f1",
        "font_size": 36,
        "width": 720,
        "height": 1280,
        "fps": 24,
        "line_chars": 14,
    },
}


def check_dependencies():
    """检查必需的命令行工具"""
    missing = []
    for cmd in ["ffmpeg", "ffprobe"]:
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            missing.append(cmd)
    if missing:
        print(f"❌ 缺少工具: {', '.join(missing)}")
        sys.exit(1)
    print("✅ 所有依赖检查通过")


def text_to_speech(text, lang="zh-cn", slow=False):
    """gTTS: 文字转语音"""
    print(f"🎤 生成语音 ({len(text)}字)...")
    tts = gTTS(text=text, lang=lang, slow=slow)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tmp.name)
    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", tmp.name],
        capture_output=True, text=True
    ).stdout.strip() or 5)
    print(f"   ✅ 语音时长: {duration:.1f}s")
    return tmp.name, duration


def wrap_text(text, chars_per_line):
    """将长文本分行"""
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        lines.extend(textwrap.wrap(paragraph, width=chars_per_line) or [paragraph])
    return lines


def get_escaped_text(text):
    """转义 ffmpeg drawtext 特殊字符"""
    return (text.replace("'", "’")
                .replace(":", "\\:")
                .replace("'", "\\'"))


def create_video(style, lines, audio_path, output_path, duration, font_file=None):
    """ffmpeg: 合成最终视频（文字叠加 + 背景音乐/配音）"""
    cfg = STYLES.get(style, STYLES["default"])
    w, h = cfg["width"], cfg["height"]
    fps = cfg["fps"]
    font_color = cfg["text_color"]
    bg_color = cfg["bg_color"]

    # 计算每段文字显示时长
    line_count = max(len(lines), 1)
    per_line_duration = duration / line_count

    # 构建画中画 filter_complex
    # 使用 subtitles 或 drawtext 来叠加文字
    filter_parts = []
    current_filter = f"[0:v]drawbox=color={bg_color}@1:width={w}:height={h}:t=fill"

    for i, line in enumerate(lines):
        # 居中显示，逐行从顶部开始
        y_pos = int(h * 0.3 + i * 60)
        escaped = get_escaped_text(line)
        
        if font_file:
            font_str = f":fontfile={font_file}"
        else:
            font_str = ""

        # 添加文字淡入淡出效果
        start_time = i * per_line_duration
        # drawtext 叠加在画布上
        text_filter = (
            f"drawtext=text='{escaped}'"
            f":fontcolor={font_color}"
            f":fontsize={cfg['font_size']}"
            f"{font_str}"
            f":x=(w-text_w)/2"
            f":y={y_pos}"
            f":enable='between(t,{start_time},{start_time + per_line_duration})'"
        )
        filter_parts.append(text_filter)

    if filter_parts:
        # 创建纯色背景 + 所有 drawtext 叠加
        bg_filter = f"color=c={bg_color}:s={w}x{h}:d={duration}[bg];"
        text_overlay = ",".join(filter_parts)
        # 使用 overlay 来合并 drawtext
        filter_complex = (
            f"{bg_filter}"
            f"[bg]{text_overlay}[vid]"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[vid]",
            "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
    else:
        # 无文字，纯图片 + 音频
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s={w}x{h}:d={duration}",
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]

    print(f"🎬 合成视频 ({len(lines)} 行文字, {duration:.0f}s)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        print(f"❌ 视频合成失败:\n{result.stderr[:500]}")
        return False
    
    size = os.path.getsize(output_path) / (1024*1024)
    print(f"   ✅ 视频生成: {output_path} ({size:.1f}MB)")
    return True


def create_title_card(title, duration=3, style="default"):
    """生成片头"""
    cfg = STYLES.get(style, STYLES["default"])
    w, h = cfg["width"], cfg["height"]
    
    output = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    escaped = get_escaped_text(title)
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={cfg['bg_color']}:s={w}x{h}:d={duration}",
        "-vf", (
            f"drawtext=text='{escaped}'"
            f":fontcolor={cfg['text_color']}"
            f":fontsize={cfg['font_size'] + 8}"
            f":x=(w-text_w)/2"
            f":y=(h-text_h)/2"
            f":enable='between(t,0,{duration})'"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        output
    ]
    
    subprocess.run(cmd, capture_output=True, timeout=30)
    return output


def produce_video(topic, script_text, output_path, style="default"):
    """
    主流程:
    1. 语音合成 (gTTS)
    2. 文字分行
    3. 视频合成
    """
    print(f"\n{'='*50}")
    print(f"🎥 ComputeHub 视频生产线")
    print(f"📌 主题: {topic}")
    print(f"📝 文案: {len(script_text)}字")
    print(f"🎨 风格: {style}")
    print(f"{'='*50}\n")

    # Step 1: TTS
    audio_file, duration = text_to_speech(script_text)

    # Step 2: 分行
    cfg = STYLES[style]
    lines = wrap_text(script_text, cfg["line_chars"])
    print(f"📄 分 {len(lines)} 行显示")

    # Step 3: 合成视频
    success = create_video(style, lines, audio_file, output_path, duration)
    
    # 清理
    os.unlink(audio_file)
    
    if success:
        print(f"\n✅ 视频生产线完成!")
        print(f"   📁 {output_path}")
        print(f"   📏 {os.path.getsize(output_path) / (1024*1024):.1f}MB")
        return {"status": "success", "output": output_path, "duration": duration}
    else:
        return {"status": "failed", "error": "video composition failed"}


def main():
    parser = argparse.ArgumentParser(description="ComputeHub 视频生产线")
    parser.add_argument("--topic", required=True, help="视频主题")
    parser.add_argument("--script", help="文案内容（直接传入）")
    parser.add_argument("--script-file", help="文案文件")
    parser.add_argument("--output", default="/tmp/video_output.mp4", help="输出路径")
    parser.add_argument("--style", default="default", choices=STYLES.keys(), help="视频风格")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出（用于 ComputeHub 任务）")
    
    args = parser.parse_args()
    
    # 获取文案
    if args.script:
        script = args.script
    elif args.script_file:
        with open(args.script_file) as f:
            script = f.read().strip()
    else:
        # 无文案则用主题生成简短示例
        script = f"欢迎收看本期节目。今天我们来聊聊：{args.topic}。这是一个由ComputeHub自动生成的视频。感谢您的观看，我们下期再见。"
    
    result = produce_video(args.topic, script, args.output, args.style)
    
    if args.json:
        print(json.dumps(result))
    else:
        print(f"\n💡 提示: 用 --json 输出 JSON 格式，方便 ComputeHub 任务解析")


if __name__ == "__main__":
    main()
