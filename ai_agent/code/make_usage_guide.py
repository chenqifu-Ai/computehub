#!/usr/bin/env python3
"""
📖 ComputeHub 使用说明视频
========================
7 节: 总览 → Gateway → Worker → TUI → Gallery → 下载 → 结束
"""
import subprocess, os, sys, json, time, tempfile

DEBUG = True
GALLERY = "/var/computehub/gallery"
FONT = "/system/fonts/MiSansVF.ttf"
OUTPUT = f"{GALLERY}/computehub_usage_guide.mp4"
W, H = 1920, 1080
FPS = 24

def log(msg):
    if DEBUG: print(f"[INFO] {msg}")

def run(cmd, desc="", timeout=90):
    log(f"▶ {desc}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(f"[ERROR] {desc}")
        print(r.stderr[-300:])
        return False
    return True

def tf(text):
    """Write text to temp file for ffmpeg"""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    f.write(text)
    f.close()
    return f.name

def make_seg(num, texts, duration=6, bg="#0d1117"):
    """Create a video segment"""
    out = f"/tmp/seg_{num}.mp4"
    vf_parts = []
    temp_files = []

    for txt, size, ypos, color, has_box in texts:
        if size <= 0:
            continue
        tf_path = tf(txt)
        temp_files.append(tf_path)
        opts = (
            f"drawtext=textfile={tf_path}:fontfile={FONT}:"
            f"fontsize={size}:fontcolor={color}:"
            f"x=(w-text_w)/2:y={ypos}"
        )
        if has_box:
            opts += ":box=1:boxcolor=black@0.2:boxborderw=10"
        opts += ":shadowcolor=black@0.4:shadowx=2:shadowy=2"
        vf_parts.append(opts)

    if not vf_parts:
        return None

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg}:s={W}x{H}:d={duration}:r={FPS}",
        "-c:v", "libx264", "-preset", "fast",
        "-crf", "23", "-pix_fmt", "yuv420p",
        "-vf", ",".join(vf_parts),
        "-movflags", "+faststart", out
    ]

    ok = run(cmd, f"片段{num}")
    for p in temp_files:
        try: os.unlink(p)
        except: pass
    return out if ok else None

def main():
    log("🎬 ComputeHub 使用说明视频生成中...")
    segments = []

    # ── 1. 开场 ──
    s = make_seg(0, [
        ("ComputeHub 使用说明", 68, 180, "#58a6ff", False),
        ("算力调度平台 v0.7.7", 40, 300, "#8b949e", False),
        ("", 0, 0, "#000", False),
        ("三种模式  |  一个二进制", 36, 440, "#c9d1d9", False),
        ("Gateway  Worker  TUI", 36, 500, "#3fb950", False),
        ("", 0, 0, "#000", False),
        ("全平台支持  |  开源免费", 30, 580, "#484f58", False),
    ], duration=7)
    if s: segments.append(s)

    # ── 2. 总览 ──
    s = make_seg(1, [
        ("📋 支持的子命令", 52, 100, "#f0f6fc", False),
        ("", 0, 0, "#000", False),
        ("gateway   启动 HTTP 服务 / 调度中心", 34, 240, "#58a6ff", False),
        ("worker    启动计算节点 接入集群", 34, 310, "#79c0ff", False),
        ("tui       启动终端管理界面", 34, 380, "#f78c6c", False),
        ("", 0, 0, "#000", False),
        ("version   显示版本号", 30, 480, "#8b949e", False),
        ("help      查看帮助信息", 30, 540, "#8b949e", False),
        ("", 0, 0, "#000", False),
        ("computehub --help  查看全部", 30, 620, "#3fb950", False),
    ], duration=8)
    if s: segments.append(s)

    # ── 3. Gateway ──
    s = make_seg(2, [
        ("🖥 Gateway 服务", 52, 80, "#f0f6fc", False),
        ("启动调度中心：", 34, 190, "#8b949e", False),
        ("computehub gateway --port 8282", 32, 280, "#58a6ff", True),
        ("", 0, 0, "#000", False),
        ("功能：", 30, 380, "#8b949e", False),
        ("节点注册/心跳/任务调度", 30, 430, "#c9d1d9", False),
        ("Gallery 作品广场 / HTTP下载", 30, 480, "#c9d1d9", False),
        ("仪表盘 / 在线升级", 30, 530, "#c9d1d9", False),
        ("", 0, 0, "#000", False),
        ("默认端口 8282  |  访问 http://ip:8282", 28, 610, "#3fb950", False),
    ], duration=9)
    if s: segments.append(s)

    # ── 4. Worker ──
    s = make_seg(3, [
        ("⚡ Worker 计算节点", 52, 70, "#f0f6fc", False),
        ("接入集群执行任务：", 32, 180, "#8b949e", False),
        ("computehub worker --gw http://192.168.1.17:8282 --node-id gpu-01", 28, 270, "#58a6ff", True),
        ("", 0, 0, "#000", False),
        ("--gw <url>     Gateway 地址", 28, 380, "#c9d1d9", False),
        ("--node-id      节点名称", 28, 430, "#c9d1d9", False),
        ("--gpu-type     GPU 型号 (自动检测)", 28, 480, "#c9d1d9", False),
        ("--concurrent   最大并发数 (默认 4)", 28, 530, "#c9d1d9", False),
        ("--region       区域标签 cn-east", 28, 580, "#c9d1d9", False),
        ("--heartbeat    心跳间隔秒 (默认 25)", 28, 630, "#c9d1d9", False),
    ], duration=10)
    if s: segments.append(s)

    # ── 5. TUI ──
    s = make_seg(4, [
        ("📟 TUI 终端管理界面", 52, 120, "#f0f6fc", False),
        ("实时查看集群状态：", 34, 240, "#8b949e", False),
        ("computehub tui --gw http://192.168.1.17:8282", 30, 330, "#58a6ff", True),
        ("", 0, 0, "#000", False),
        ("节点列表   |   任务队列", 34, 450, "#c9d1d9", False),
        ("实时监控   |   结果查看", 34, 510, "#c9d1d9", False),
        ("", 0, 0, "#000", False),
        ("交互式界面，支持键盘导航", 32, 600, "#3fb950", False),
    ], duration=8)
    if s: segments.append(s)

    # ── 6. Gallery / 下载 ──
    s = make_seg(5, [
        ("🎨 Gallery 作品广场", 52, 80, "#f0f6fc", False),
        ("浏览器访问 Gallery 页面：", 34, 200, "#8b949e", False),
        ("http://192.168.1.17:8282/api/v1/gallery", 28, 300, "#58a6ff", True),
        ("", 0, 0, "#000", False),
        ("直接查看/播放所有产出", 32, 420, "#c9d1d9", False),
        ("视频/图片/文件 一键下载", 32, 480, "#c9d1d9", False),
        ("", 0, 0, "#000", False),
        ("下载二进制：/api/v1/download?file=computehub&platform=linux-arm64", 24, 580, "#79c0ff", False),
        ("校验：curl -O /api/v1/download?file=sha256sums-0.7.7.txt", 24, 640, "#8b949e", False),
    ], duration=10)
    if s: segments.append(s)

    # ── 7. 片尾 ──
    s = make_seg(6, [
        ("✅ 快速上手", 56, 200, "#3fb950", False),
        ("1. 启动 Gateway", 34, 320, "#c9d1d9", False),
        ("2. 启动 Worker 节点", 34, 390, "#c9d1d9", False),
        ("3. 通过 TUI 或 API 提交任务", 34, 460, "#c9d1d9", False),
        ("4. Gallery 查看产出", 34, 530, "#c9d1d9", False),
        ("", 0, 0, "#000", False),
        ("文档: github.com/chenqifu-Ai/computehub", 28, 620, "#58a6ff", False),
    ], duration=8)
    if s: segments.append(s)

    if not segments:
        print("[ERROR] 所有片段生成失败！")
        sys.exit(1)

    log(f"✅ 生成 {len(segments)}/{7} 个片段")

    # Merge
    concat_file = "/tmp/concat_guide.txt"
    with open(concat_file, "w") as f:
        for s in segments:
            f.write(f"file '{s}'\n")

    log("🎬 合并...")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast",
        "-crf", "23", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", OUTPUT
    ]
    if not run(cmd, "合并"): sys.exit(1)

    # Add music
    music = os.path.join(GALLERY, "music.mp3")
    if os.path.exists(music):
        log("🎵 加音乐...")
        tmp = OUTPUT + ".tmp.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", OUTPUT, "-i", music,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-filter_complex", "[1:a]volume=0.12[a]",
            "-map", "0:v:0", "-map", "[a]", tmp
        ]
        if run(cmd, "加音乐"):
            os.replace(tmp, OUTPUT)

    # Cleanup
    for s in segments:
        try: os.remove(s)
        except: pass
    try: os.remove(concat_file)
    except: pass

    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    total_dur = 7 + 8 + 9 + 10 + 8 + 10 + 8

    log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log(f"✅ {OUTPUT}")
    log(f"📏 {size_mb:.1f} MB | ⏱ ~{total_dur}s | 🎬 {len(segments)}/7")
    print(json.dumps({
        "title": "ComputeHub 使用说明",
        "desc": "ComputeHub 算力调度平台完整使用指南：Gateway / Worker / TUI / Gallery",
        "tags": ["使用说明", "ComputeHub", "教程"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_sec": total_dur,
        "url": "/api/v1/gallery?file=usage_guide.mp4"
    }))

if __name__ == "__main__":
    main()
