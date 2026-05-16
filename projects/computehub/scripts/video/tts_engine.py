#!/usr/bin/env python3
"""
🗣️ ComputeHub 语音引擎
基于 edge-tts，支持中文男声/女声

坑修复记录 (2026-05-16):
  #6 AAC编码浏览器不兼容 → 统一输出 MP3
  重试机制：失败自动重试 3 次
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import re
from pathlib import Path


# ── 语音配置 ──────────────────────────────────────────────────

VOICES = {
    "yunxi": "zh-CN-YunXiNeural",      # 男声
    "xiaoxiao": "zh-CN-XiaoxiaoNeural", # 女声
    "yunyang": "zh-CN-YunYangNeural",   # 男声 (活力)
    "xiaochen": "zh-CN-XiaochenNeural", # 女声 (温柔)
}

DEFAULT_VOICE = "yunxi"


def get_audio_duration(audio_path: str) -> float:
    """获取音频时长（秒）— 修复 #7: 用正则提取数字"""
    if not os.path.exists(audio_path):
        return 0.0
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = result.stdout.strip()
        # 修复 #7: 用 re.search 提取数字，不假设纯数字
        m = re.search(r"(\d+\.?\d*)", out)
        return float(m.group(1)) if m else 0.0
    except Exception:
        return 0.0


def check_edge_tts() -> bool:
    """检查 edge-tts 是否可用"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "edge_tts", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def generate_speech(text: str, output_path: str,
                     voice: str = DEFAULT_VOICE,
                     rate: str = "+0%",
                     volume: str = "+0%") -> bool:
    """生成语音，支持自动重试

    Args:
        text: 要朗读的文本
        output_path: 输出音频路径
        voice: 语音角色
        rate: 语速 ("+0%", "+20%", "-10%")
        volume: 音量 ("+0%", "+50%")

    Returns:
        bool: 是否成功
    """
    if not text or not text.strip():
        return False

    voice_id = VOICES.get(voice, VOICES[DEFAULT_VOICE])

    max_retries = 3
    for attempt in range(max_retries):
        try:
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--text", text,
                "--voice", voice_id,
                "--rate", rate,
                "--volume", volume,
                "--write-media", output_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=120,  # 长文本超时 2 分钟
            )

            if result.returncode == 0 and os.path.exists(output_path):
                size = os.path.getsize(output_path)
                if size > 100:  # 至少 100 字节
                    return True
                else:
                    print(f"  ⚠️ TTS 输出太小 ({size} bytes)，重试...")
            else:
                print(f"  ⚠️ TTS 失败 (attempt {attempt+1}): {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            print(f"  ⚠️ TTS 超时 (attempt {attempt+1})")
        except Exception as e:
            print(f"  ⚠️ TTS 异常 (attempt {attempt+1}): {e}")

        if attempt < max_retries - 1:
            time.sleep(1)  # 等一秒再重试

    return False


async def generate_speech_async(text: str, output_path: str,
                                 voice: str = DEFAULT_VOICE,
                                 rate: str = "+0%",
                                 volume: str = "+0%") -> bool:
    """异步生成语音（使用 edge-tts 异步 API）"""
    try:
        import edge_tts

        voice_id = VOICES.get(voice, VOICES[DEFAULT_VOICE])
        communicate = edge_tts.Communicate(text, voice_id, rate=rate, volume=volume)
        await communicate.save(output_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return True
        return False
    except ImportError:
        # fallback 到 CLI
        return generate_speech(text, output_path, voice, rate, volume)
    except Exception as e:
        print(f"  ⚠️ 异步 TTS 失败: {e}")
        return False


def generate_script_audio(lines: list, output_dir: str = None,
                           voice: str = DEFAULT_VOICE) -> list:
    """为脚本每一行生成独立音频文件

    Returns:
        [(audio_path, duration_sec), ...]
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tts_")

    results = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        audio_path = os.path.join(output_dir, f"speech_{i:04d}.mp3")  # 修复 #6: 输出 MP3
        ok = generate_speech(line, audio_path, voice=voice)
        if ok:
            dur = get_audio_duration(audio_path)
            results.append((audio_path, dur))
            print(f"  🗣️ 语音 {i}: {line[:30]}... ({dur:.1f}s)")
        else:
            print(f"  ⚠️ 语音 {i} 生成失败")

    return results


# ── 测试 ──────────────────────────────────────────────────────

def test_tts():
    """测试 TTS 引擎"""
    ok = check_edge_tts()
    print(f"edge-tts 可用: {ok}")
    if ok:
        out = "/tmp/test_tts.mp3"
        success = generate_speech("你好，欢迎使用 ComputeHub 视频生成系统。", out)
        print(f"生成测试语音: {'✅' if success else '❌'}")
        if success:
            dur = get_audio_duration(out)
            print(f"  时长: {dur:.1f}s, 大小: {os.path.getsize(out)} bytes")


if __name__ == "__main__":
    test_tts()
