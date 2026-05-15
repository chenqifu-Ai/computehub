#!/usr/bin/env python3
"""
ComputeHub 30秒介绍视频生成脚本
展示3张产品图 + 文字说明 + 背景音乐
"""
import subprocess, os, json

DEBUG = True

GALLERY = "/var/computehub/gallery"
FONT = "/system/fonts/MiSansVF.ttf"
MUSIC = f"{GALLERY}/music.mp3"
IMAGES = [
    f"{GALLERY}/1778807712568.jpg",
    f"{GALLERY}/1778807724550.jpg",
    f"{GALLERY}/1778807733491.jpg",
]
OUTPUT = f"{GALLERY}/computehub_intro_30s.mp4"

W, H = 1920, 1080
FPS = 24

def log(msg):
    if DEBUG: print(f"[INFO] {msg}")

def run(cmd, desc=""):
    log(f"Running: {desc or cmd[:80]}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"[ERROR] {desc or cmd}")
        print(r.stderr[-1000:])
        return False
    if r.stderr:
        lines = [l for l in r.stderr.split('\n') if l.strip()]
        for l in lines[-5:]:
            log(l[:120])
    return True

def draw_frame(num, image_path, text_lines, duration=8, bg="#0a0a1a"):
    """Create a video segment with image + text overlay"""
    out = f"/tmp/seg_{num}.mp4"
    
    # Scale image to fit 1920x1080 with letterbox
    # Image is 3072x4096 (portrait 3:4), need to fit into 16:9
    # Scale height to 1080 then pad sides to 1920
    filter_complex = (
        f"[0:v]scale='if(gt(dar,16/9),1920,-1)':'if(gt(dar,16/9),-1,1080)',"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color={bg},"
        f"setsar=1,format=yuv420p[bgv];"
    )
    
    # Add text overlays
    text_filter = ""
    prev_label = "bgv"
    for i, line in enumerate(text_lines):
        txt, fontsize, ypos, color = line
        label = f"txt{i}"
        box = "box=1:boxcolor=black@0.4:boxborderw=15"
        text_filter += (
            f"[{prev_label}]drawtext="
            f"text='{txt}':"
            f"fontfile={FONT}:"
            f"fontsize={fontsize}:"
            f"fontcolor={color}:"
            f"x=(w-text_w)/2:"
            f"y={ypos}:"
            f"{box}[{label}];"
        )
        prev_label = label
    
    filter_complex += text_filter
    filter_complex = filter_complex.rstrip(';')
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-c:v", "libx264",
        "-t", str(duration),
        "-s", f"{W}x{H}",
        "-filter_complex", filter_complex,
        "-map", f"[{prev_label}]",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        out
    ]
    
    if run(cmd, f"Segment {num} - {duration}s"):
        return out
    return None

def title_card(text_lines, duration=4, bg="#0a0a1a"):
    """Create a title/end card"""
    out = "/tmp/title_card.mp4"
    
    filter_complex = f"color=c={bg}:s={W}x{H}:d={duration}[bg];"
    prev_label = "bg"
    for i, line in enumerate(text_lines):
        txt, fontsize, ypos, color = line
        label = f"txt{i}"
        box = "box=1:boxcolor=black@0.5:boxborderw=20"
        filter_complex += (
            f"[{prev_label}]drawtext="
            f"text='{txt}':"
            f"fontfile={FONT}:"
            f"fontsize={fontsize}:"
            f"fontcolor={color}:"
            f"x=(w-text_w)/2:"
            f"y={ypos}:"
            f"{box}[{label}];"
        )
        prev_label = label
    
    filter_complex = filter_complex.rstrip(';')
    
    cmd = [
        "ffmpeg", "-y",
        "-filter_complex", filter_complex,
        "-map", f"[{prev_label}]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        out
    ]
    
    if run(cmd, "Title card"):
        return out
    return None

def concat_with_audio(segments, audio_path, output):
    """Concatenate all segments and add background audio"""
    
    # Create concat file
    concat_content = "\n".join([f"file '{s}'" for s in segments])
    with open("/tmp/concat_list.txt", "w") as f:
        f.write(concat_content)
    
    # First concat all video segments
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "/tmp/concat_list.txt",
        "-c", "copy",
        "/tmp/combined_noaudio.mp4"
    ]
    if not run(cmd_concat, "Concatenate segments"):
        return None
    
    # Get total duration
    r = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        "/tmp/combined_noaudio.mp4"
    ], capture_output=True, text=True, timeout=10)
    video_dur = float(r.stdout.strip())
    
    # Get audio duration
    r = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ], capture_output=True, text=True, timeout=10)
    audio_dur = float(r.stdout.strip())
    
    log(f"Video: {video_dur:.1f}s, Audio: {audio_dur:.1f}s")
    
    # Loop audio to match video duration, volume 0.25
    loop_count = int(video_dur / audio_dur) + 1
    afilter = f"aloop=loop={loop_count}:size=1000000,volume=0.15,atrim=duration={video_dur}"
    
    cmd_final = [
        "ffmpeg", "-y",
        "-i", "/tmp/combined_noaudio.mp4",
        "-i", audio_path,
        "-filter_complex", f"[1:a]{afilter}[aud]",
        "-map", "0:v",
        "-map", "[aud]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output
    ]
    
    if run(cmd_final, "Final mixing"):
        log(f"✅ Video saved: {output}")
        r2 = subprocess.run(["ls", "-lh", output], capture_output=True, text=True)
        log(r2.stdout.strip())
        return output
    return None

def main():
    log("Starting ComputeHub 30s intro video generation...")
    
    # 1. Title card (4s)
    log("Creating title card...")
    title = title_card([
        ("ComputeHub", 80, "(h-text_h)/2-60", "#00d4ff"),
        ("AI 集群计算平台", 40, "(h-text_h)/2+20", "#7b2ff7"),
        ("分布式计算 · 智能调度 · 生产就绪", 28, "(h-text_h)/2+90", "#888888"),
    ], duration=4)
    if not title: return
    
    # 2. Image 1 - distributed computing (8s)
    log("Creating segment 1...")
    seg1 = draw_frame(1, IMAGES[0], [
        ("智能调度系统", 52, "70", "#f7971e"),
        ("动态资源分配 · 任务自动分发 · 负载均衡", 30, "140", "#cccccc"),
        ("智能分析计算负载，自动分配到最优节点", 22, "H-90", "#888888"),
    ], duration=8)
    if not seg1: return
    
    # 3. Image 2 - cross-platform (8s)
    seg2 = draw_frame(2, IMAGES[1], [
        ("全平台支持", 52, "70", "#4caf50"),
        ("Linux · Windows · Android · macOS", 30, "140", "#cccccc"),
        ("一套集群，管理所有设备的算力资源", 22, "H-90", "#888888"),
    ], duration=8)
    if not seg2: return
    
    # 4. Image 3 - open source (8s)
    seg3 = draw_frame(3, IMAGES[2], [
        ("开源 · 开放 · 自由", 52, "70", "#e91e63"),
        ("企业级计算平台，MIT 开源协议", 30, "140", "#cccccc"),
        ("立即部署，释放你的算力潜能", 22, "H-90", "#888888"),
    ], duration=8)
    if not seg3: return
    
    # 5. End card (2s)
    end = title_card([
        ("小智影业 出品", 48, "(h-text_h)/2-40", "#f7971e"),
        ("Powered by ComputeHub", 30, "(h-text_h)/2+30", "#888888"),
    ], duration=2, bg="#1a1a2e")
    if not end: return
    
    # 6. Concatenate all
    log("Concatenating segments and adding music...")
    segments = [title, seg1, seg2, seg3, end]
    concat_with_audio(segments, MUSIC, OUTPUT)
    
    log("Done! 🎬")

if __name__ == "__main__":
    main()
