#!/usr/bin/env python3
"""
🎵 视频音频修复补丁
==================
修复两个问题：
1. 声音像快进 — edge-tts 16kHz 与 44kHz 不匹配
2. 声音重复播 — BGM 双循环叠加

用法：
  python3 fix_video_audio.py /path/to/video_pipeline.py
"""

import sys
import os

def fix_audio_sampling(content: str) -> str:
    """修复1：在所有音频编码加 -ar 44100 强制统一采样率"""
    fixes = 0
    
    # 1. 段编码 - 音频部分
    old1 = '''        cmd.extend([
            "-c:v", "libx264",
            "-c:a", "libmp3lame",
            "-t", str(duration),'''
    new1 = '''        cmd.extend([
            "-c:v", "libx264",
            "-c:a", "libmp3lame",
            "-ar", "44100",
            "-t", str(duration),'''
    if old1 in content:
        content = content.replace(old1, new1)
        fixes += 1
        print("  ✅ 修复1a: 段编码音频采样率")
    
    # 2. BGM混音部分 - 用 concat 替代双循环
    old_bgm_loop = '''    if bgm_dur < video_dur:
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
        ]'''
    
    new_bgm = '''    # ★ 用 concat demuxer 做纯 BGM 循环，避免 -stream_loop + aloop 双循环
    if bgm_dur < video_dur:
        loops = int(video_dur / bgm_dur) + 2
        concat_bgm = os.path.join(os.path.dirname(video_path), "_bgm_loop.txt")
        with open(concat_bgm, "w") as f:
            for _ in range(loops):
                f.write(f"file '{os.path.abspath(bgm_path)}'\\n")
        looped_bgm = os.path.join(os.path.dirname(video_path), "_bgm_loop.mp3")
        loop_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_bgm,
            "-c", "copy",
            "-t", str(video_dur),
            looped_bgm,
        ]
        subprocess.run(loop_cmd, capture_output=True, timeout=60)
        if os.path.exists(concat_bgm):
            os.remove(concat_bgm)

        if os.path.exists(looped_bgm) and os.path.getsize(looped_bgm) > 0:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", looped_bgm,
                "-filter_complex",
                f"[1:a]volume={music_volume}[music];"
                f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]",
                "-map", "0:v", "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "libmp3lame",
                "-ar", "44100",
                "-shortest",
                output_path,
            ]
            ok = run_ffmpeg(cmd, "混音背景音乐", timeout=180)
            if os.path.exists(looped_bgm):
                os.remove(looped_bgm)
            return ok
        
        # fallback
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={music_volume}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "copy",
            "-c:a", "libmp3lame",
            "-ar", "44100",
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
            "-ar", "44100",
            "-shortest",
            output_path,
        ]'''

    if old_bgm_loop in content:
        content = content.replace(old_bgm_loop, new_bgm)
        fixes += 1
        print("  ✅ 修复2a: BGM 双循环 -> concat 单循环")
    else:
        # 尝试已经部分修复的版本
        print("  ⚠️ BGM混合代码模式不匹配，手动检查...")
        # 检查是否已修复（含 -ar 44100 的新版本）
        if "-ar", "44100" in content and "concat_bgm" in content:
            print("  ✅ BGM已修复，跳过")
            fixes += 1
        else:
            print("  ❌ 无法自动修复BGM循环，需要手动替换")

    return content, fixes


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fix_video_audio.py /path/to/video_pipeline.py")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        sys.exit(1)

    print(f"🔧 修复视频音频管线: {path}")
    
    with open(path, "r") as f:
        content = f.read()
    
    # 备份
    bak = path + ".bak"
    if not os.path.exists(bak):
        with open(bak, "w") as f:
            f.write(content)
        print(f"  📦 备份: {bak}")
    
    content, fixes = fix_audio_sampling(content)
    
    with open(path, "w") as f:
        f.write(content)
    
    print(f"\n✅ 修复完成，共 {fixes} 处改动")
    print(f"📁 原文件备份: {bak}")


if __name__ == "__main__":
    main()
