#!/usr/bin/env python3
"""
🗣️ ComputeHub 语音引擎 v2
==========================
基于 MeloTTS（开源，CPU 可跑，国内直连）
不支持 GPU 的服务器上首选方案。

回退机制: MeloTTS → edge-tts (海外) → 静默跳过

用法:
  python3 tts_engine.py                     # 测试
  python3 tts_engine.py --benchmark "你好"  # 基准测试
"""

import os
import re
import sys
import json
import time
import subprocess
import tempfile
from pathlib import Path


# ── 配置 ──────────────────────────────────────────────────────

VOICE_MAP = {
    # 标准中文字幕配音（用于视频脚本朗读）
    "yunxi":    {"engine": "melo",   "speaker": "ZH",   "language": "ZH",  "desc": "中文男声（MeloTTS 默认）"},
    "xiaoxiao": {"engine": "melo",   "speaker": "ZH",   "language": "ZH",  "desc": "中文女声（MeloTTS 默认）"},
    "yunyang":  {"engine": "melo",   "speaker": "ZH",   "language": "ZH",  "desc": "中文男声（MeloTTS 默认）"},
    "xiaochen": {"engine": "melo",   "speaker": "ZH",   "language": "ZH",  "desc": "中文女声（MeloTTS 默认）"},
    # 英语备用
    "en_male":  {"engine": "melo",   "speaker": "EN",   "language": "EN",  "desc": "英文男声"},
    "en_female":{"engine": "melo",   "speaker": "EN_US","language": "EN",  "desc": "英文女声"},
}

DEFAULT_VOICE = "yunxi"

# ── 引擎检测 ──────────────────────────────────────────────────

def _check_melo_tts() -> bool:
    """检查 MeloTTS 是否可导入"""
    try:
        from melotts import MeloTTS
        return True
    except ImportError:
        return False


def _check_edge_tts() -> bool:
    """检查 edge-tts 是否可导入（海外备用）"""
    try:
        import edge_tts
        return True
    except ImportError:
        return False


def _check_available_engines() -> list:
    """返回当前可用的引擎列表"""
    engines = []
    if _check_melo_tts():
        engines.append("melo")
    if _check_edge_tts():
        engines.append("edge")
    return engines


# ── 核心 TTS ──────────────────────────────────────────────────

# MeloTTS 全局单例（延迟初始化）
_MELO_INSTANCE = None


def _get_melo() -> object:
    """获取 MeloTTS 实例（懒加载）"""
    global _MELO_INSTANCE
    if _MELO_INSTANCE is None:
        from melotts import MeloTTS
        print("  🔄 初始化 MeloTTS（首次加载较慢 ~5-10s）...", file=sys.stderr)
        t0 = time.time()
        _MELO_INSTANCE = MeloTTS()
        elapsed = time.time() - t0
        print(f"  ✅ MeloTTS 初始化完成 ({elapsed:.1f}s)", file=sys.stderr)
    return _MELO_INSTANCE


def generate_speech(text: str, output_path: str,
                    voice: str = DEFAULT_VOICE,
                    rate: str = "+0%",
                    volume: str = "+0%") -> bool:
    """生成语音，自动选择最佳可用引擎

    引擎选择:
      1. MeloTTS（首选，纯CPU，国内直连）
      2. edge-tts（备选，需要海外网络）
      3. 失败返回 False

    Args:
        text: 要朗读的文本
        output_path: 输出音频路径（MP3）
        voice: 语音角色 (yunxi/xiaoxiao/yunyang/xiaochen)
        rate: 语速 (仅 edge-tts 支持)
        volume: 音量 (仅 edge-tts 支持)

    Returns:
        bool: 是否成功
    """
    if not text or not text.strip():
        return False

    voice_cfg = VOICE_MAP.get(voice, VOICE_MAP[DEFAULT_VOICE])
    engines = _check_available_engines()

    if not engines:
        print("  ⚠️ 无可用 TTS 引擎！请安装 MeloTTS: pip install melotts", file=sys.stderr)
        return False

    # 1) 尝试 MeloTTS
    if "melo" in engines:
        return _generate_melo(text, output_path, voice_cfg)

    # 2) 回退 edge-tts
    if "edge" in engines:
        return _generate_edge(text, output_path, voice, rate, volume)

    return False


def _generate_melo(text: str, output_path: str, voice_cfg: dict) -> bool:
    """使用 MeloTTS 生成语音"""
    try:
        melo = _get_melo()
        speaker = voice_cfg.get("speaker", "ZH")
        language = voice_cfg.get("language", "ZH")

        # MeloTTS 输出 WAV，转 MP3
        wav_path = output_path.replace(".mp3", ".wav")
        if wav_path == output_path:
            wav_path = output_path + ".wav"

        melo.tts_to_file(text, wav_path, speaker=speaker, language=language)

        # 转 MP3（兼容之前流程）
        if wav_path != output_path and os.path.exists(wav_path):
            subprocess.run(
                ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame",
                 "-q:a", "2", output_path],
                capture_output=True, timeout=30,
            )
            os.remove(wav_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return True
        return False

    except Exception as e:
        print(f"  ⚠️ MeloTTS 失败: {e}", file=sys.stderr)
        return False


def _generate_edge(text: str, output_path: str, voice: str,
                   rate: str, volume: str) -> bool:
    """使用 edge-tts 生成语音（海外备用）"""
    import edge_tts

    EDGE_VOICES = {
        "yunxi": "zh-CN-YunXiNeural",
        "xiaoxiao": "zh-CN-XiaoxiaoNeural",
        "yunyang": "zh-CN-YunYangNeural",
        "xiaochen": "zh-CN-XiaochenNeural",
    }
    voice_id = EDGE_VOICES.get(voice, EDGE_VOICES[DEFAULT_VOICE])

    max_retries = 2
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(
                text, voice_id, rate=rate, volume=volume
            )
            # edge-tts 原生支持 MP3
            import asyncio
            asyncio.run(communicate.save(output_path))

            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"  ⚠️ edge-tts 失败: {e}", file=sys.stderr)

    return False


# ── 批量语音生成 ──────────────────────────────────────────────

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
        audio_path = os.path.join(output_dir, f"speech_{i:04d}.mp3")
        ok = generate_speech(line, audio_path, voice=voice)
        if ok:
            dur = get_audio_duration(audio_path)
            results.append((audio_path, dur))
            print(f"  🗣️ 语音 {i}: {line[:30]}... ({dur:.1f}s)")
        else:
            print(f"  ⚠️ 语音 {i} 生成失败")

    return results


def get_audio_duration(audio_path: str) -> float:
    """获取音频时长（秒）"""
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
        m = re.search(r"(\d+\.?\d*)", out)
        return float(m.group(1)) if m else 0.0
    except Exception:
        return 0.0


# ── 安装辅助 ──────────────────────────────────────────────────

def auto_install_melo():
    """自动安装 MeloTTS（可选依赖）"""
    if _check_melo_tts():
        return True
    print("📦 正在安装 MeloTTS + PyTorch (CPU版)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "melotts"],
            check=True, timeout=300,
        )
        print("✅ 安装成功")
        return True
    except Exception as e:
        print(f"❌ 安装失败: {e}")
        return False


# ── 测试 ──────────────────────────────────────────────────────

def test_tts():
    """测试 TTS 引擎"""
    engines = _check_available_engines()
    print(f"🔍 可用引擎: {engines if engines else '❌ 无'}")

    if "melo" in engines:
        print("\n--- MeloTTS 测试 ---")
        out = "/tmp/test_tts_melo.mp3"
        success = generate_speech(
            "你好，欢迎使用 ComputeHub 视频生成系统。",
            out, voice="yunxi"
        )
        print(f"  MeloTTS: {'✅' if success else '❌'}")
        if success:
            dur = get_audio_duration(out)
            print(f"  时长: {dur:.1f}s, 大小: {os.path.getsize(out)} bytes")

    if "edge" in engines:
        print("\n--- edge-tts 测试 ---")
        out = "/tmp/test_tts_edge.mp3"
        success = generate_speech(
            "你好，这是 edge-tts 备用引擎。",
            out, voice="yunxi"
        )
        print(f"  edge-tts: {'✅' if success else '❌'}")
        if success:
            dur = get_audio_duration(out)
            print(f"  时长: {dur:.1f}s, 大小: {os.path.getsize(out)} bytes")


def benchmark(text="这是一个基准测试句子，用来测试语音合成引擎的性能和速度。"):
    """运行基准测试"""
    print(f"\n⏱️  基准测试: '{text[:30]}...'")
    print("-" * 50)
    engines = _check_available_engines()

    for engine in engines:
        out = f"/tmp/bench_{engine}.mp3"
        t0 = time.time()
        success = generate_speech(text, out, voice="yunxi")
        elapsed = time.time() - t0
        if success:
            dur = get_audio_duration(out)
            ratio = dur / elapsed if elapsed > 0 else 0
            print(f"  {engine:12s}: ✅ {elapsed:.2f}s 生成 ({dur:.1f}s 音频, {ratio:.1f}x real-time)")
        else:
            print(f"  {engine:12s}: ❌ 失败")


# ── 主入口 ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="🗣️ ComputeHub 语音引擎")
    parser.add_argument("--benchmark", type=str, help="运行基准测试")
    parser.add_argument("--install", action="store_true", help="安装 MeloTTS")
    parser.add_argument("--text", type=str, help="测试文本")
    args = parser.parse_args()

    if args.install:
        auto_install_melo()
    elif args.benchmark:
        benchmark(args.benchmark)
    elif args.text:
        out = f"/tmp/tts_{int(time.time())}.mp3"
        ok = generate_speech(args.text, out)
        print(f"{'✅' if ok else '❌'} output: {out}")
    else:
        test_tts()
