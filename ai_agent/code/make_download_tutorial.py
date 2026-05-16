#!/usr/bin/env python3
"""
📹 ComputeHub 二进制下载教程视频
=============================
6 个步骤展示如何从 Gateway 下载 binary
使用 textfile 方式避免特殊字符问题
"""
import subprocess, os, sys, json, time, tempfile

DEBUG = True
GALLERY = "/var/computehub/gallery"
FONT = "/system/fonts/MiSansVF.ttf"
OUTPUT = f"{GALLERY}/computehub_download_tutorial.mp4"
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

def write_textfile(text):
    """Write text to a temp file for ffmpeg textfile= option"""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    f.write(text)
    f.close()
    return f.name

def make_seg(num, texts, duration=6, bg="#0d1117"):
    """Create a video segment using textfile for safety"""
    out = f"/tmp/seg_{num}.mp4"
    
    # Write all text layers to separate files
    vf_parts = []
    for txt, size, ypos, color, has_box in texts:
        if size <= 0:
            continue
        tf = write_textfile(txt)
        opts = (
            f"drawtext=textfile={tf}:fontfile={FONT}:"
            f"fontsize={size}:fontcolor={color}:"
            f"x=(w-text_w)/2:y={ypos}:"
            f"shadowcolor=black@0.5:shadowx=2:shadowy=2"
        )
        if has_box:
            opts += ":box=1:boxcolor=black@0.25:boxborderw=12"
        vf_parts.append((opts, tf))
    
    if not vf_parts:
        return None
    
    vf_str = ",".join(p[0] for p in vf_parts)
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg}:s={W}x{H}:d={duration}:r={FPS}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-vf", vf_str,
        "-movflags", "+faststart",
        out
    ]
    
    ok = run(cmd, f"片段{num}")
    
    # Cleanup temp files
    for _, tf in vf_parts:
        try: os.unlink(tf)
        except: pass
    
    return out if ok else None

def main():
    log("🎬 ComputeHub 下载教程视频生成中...")
    
    segments = []
    
    # ── 片段1: 开场 ──
    seg = make_seg(0, [
        ("📦 ComputeHub 二进制下载指南", 64, 200, "#58a6ff", False),
        ("在浏览器一键下载，无需命令行", 40, 340, "#8b949e", False),
        ("支持 Linux / macOS / Windows", 36, 420, "#c9d1d9", False),
        ("v0.7.7 最新版", 32, 520, "#3fb950", False),
    ], duration=6)
    if seg: segments.append(seg)
    
    # ── 片段2: 方法1 Gallery界面 ──
    seg = make_seg(1, [
        ("🖥 方法一：Gallery 界面", 52, 120, "#f0f6fc", False),
        ("在浏览器访问 Gateway", 40, 240, "#8b949e", False),
        ("http://192.168.1.17:8282/api/v1/gallery", 28, 400, "#58a6ff", True),
        ("Gallery 页面直接显示所有可下载文件", 32, 520, "#c9d1d9", False),
        ("点击 ⬇ 下载按钮即可下载", 32, 580, "#c9d1d9", False),
    ], duration=8)
    if seg: segments.append(seg)
    
    # ── 片段3: 方法2 直接下载链接 ──
    seg = make_seg(2, [
        ("🌐 方法二：直接下载链接", 52, 80, "#f0f6fc", False),
        ("根据你的平台选择对应链接：", 36, 200, "#8b949e", False),
        ("Linux ARM64   curl -O http://ip:8282/api/v1/download?file=computehub&platform=linux-arm64", 26, 340, "#58a6ff", False),
        ("Linux AMD64   curl -O http://ip:8282/api/v1/download?file=computehub&platform=linux-amd64", 26, 400, "#79c0ff", False),
        ("macOS Intel   curl -O http://ip:8282/api/v1/download?file=computehub&platform=darwin-amd64", 26, 460, "#f78c6c", False),
        ("macOS M芯片  curl -O http://ip:8282/api/v1/download?file=computehub&platform=darwin-arm64", 26, 520, "#ff7b72", False),
        ("Windows AMD64 curl -O http://ip:8282/api/v1/download?file=computehub.exe&platform=windows-amd64", 26, 580, "#3fb950", False),
    ], duration=12)
    if seg: segments.append(seg)
    
    # ── 片段4: 校验 ──
    seg = make_seg(3, [
        ("🔐 校验文件完整性", 52, 120, "#f0f6fc", False),
        ("下载后校验 SHA256 确保文件正确", 36, 240, "#8b949e", False),
        ("curl -O http://ip:8282/api/v1/download?file=sha256sums-0.7.7.txt", 28, 380, "#58a6ff", True),
        ("sha256sum -c sha256sums-0.7.7.txt 2>/dev/null | grep -v OK", 28, 460, "#58a6ff", True),
        ("如果全部显示 ✔ OK，文件完整无误！", 34, 560, "#3fb950", False),
    ], duration=10)
    if seg: segments.append(seg)
    
    # ── 片段5: 启动 ──
    seg = make_seg(4, [
        ("🚀 启动 ComputeHub", 52, 150, "#f0f6fc", False),
        ("下载后赋予执行权限并启动：", 36, 270, "#8b949e", False),
        ("chmod +x computehub", 34, 400, "#58a6ff", True),
        ("./computehub --help", 34, 480, "#58a6ff", True),
        ("更多用法参考 GitHub 文档", 32, 580, "#c9d1d9", False),
        ("github.com/chenqifu-Ai/computehub", 28, 640, "#58a6ff", True),
    ], duration=10)
    if seg: segments.append(seg)
    
    # ── 片段6: 片尾 ──
    seg = make_seg(5, [
        ("✅ 下载完成！", 64, 250, "#3fb950", False),
        ("如有问题请提交 Issue", 36, 380, "#8b949e", False),
        ("github.com/chenqifu-Ai/computehub/issues", 28, 460, "#58a6ff", True),
        ("ComputeHub v0.7.7", 30, 580, "#484f58", False),
    ], duration=5)
    if seg: segments.append(seg)
    
    if not segments:
        print("[ERROR] 所有片段生成失败！")
        sys.exit(1)
    
    log(f"✅ 生成 {len(segments)}/{6} 个片段")
    
    # ── 合并所有片段 ──
    concat_file = "/tmp/concat_list.txt"
    with open(concat_file, "w") as f:
        for s in segments:
            f.write(f"file '{s}'\n")
    
    log("🎬 合并视频...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUTPUT
    ]
    
    if not run(cmd, "合并"):
        print("[ERROR] 合并失败")
        sys.exit(1)
    
    # ── 添加背景音乐 ──
    music = os.path.join(GALLERY, "music.mp3")
    if os.path.exists(music):
        log("🎵 添加背景音乐...")
        tmp_out = OUTPUT + ".tmp.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", OUTPUT,
            "-i", music,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-filter_complex", "[1:a]volume=0.15[a]",
            "-map", "0:v:0",
            "-map", "[a]",
            tmp_out
        ]
        if run(cmd, "加音乐"):
            os.replace(tmp_out, OUTPUT)
    
    # ── 清理 ──
    for s in segments:
        try: os.remove(s)
        except: pass
    try: os.remove(concat_file)
    except: pass
    
    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    total_dur = 6 + 8 + 12 + 10 + 10 + 5
    
    log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log(f"✅ {OUTPUT}")
    log(f"📏 {size_mb:.1f} MB | ⏱ ~{total_dur}s | 🎬 {len(segments)}/6")
    
    # Gallery 元数据
    meta = {
        "title": "ComputeHub 二进制下载教程",
        "desc": "手把手教你从 Gateway 下载 ComputeHub 二进制文件，支持多平台",
        "tags": ["教程", "ComputeHub", "下载"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_sec": total_dur,
        "url": "/api/v1/gallery?file=download_tutorial.mp4"
    }
    with open(f"{GALLERY}/download_tutorial.mp4.json", "w") as f:
        json.dump(meta, f, indent=2)
    
    print(json.dumps(meta))

if __name__ == "__main__":
    main()
