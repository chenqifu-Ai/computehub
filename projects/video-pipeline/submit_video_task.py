#!/usr/bin/env python3
"""
ComputeHub 视频生产任务 - 通过 Gateway 提交到集群执行
"""

import base64
import json
import os
import sys

# ====== 脚本代码（将被 base64 打包，通过 ComputeHub 提交到节点执行） ======

PIPELINE_SCRIPT = r'''
#!/data/data/com.termux/files/usr/bin/python3
"""视频生产线 - 在 Worker 节点上运行"""
import json, os, subprocess, sys, tempfile, textwrap
from pathlib import Path

try:
    from gtts import gTTS
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "gtts"], capture_output=True)
    from gtts import gTTS

# ====== 配置 ======
TOPIC = sys.argv[1] if len(sys.argv) > 1 else "AI改变生活"
STYLE_COLOR = {"default": "black", "finance": "darkblue", "tech": "#1a1a2e", "news": "#2c3e50"}
STYLE_TEXT = {"default": "white", "finance": "gold", "tech": "#00ff88", "news": "#ecf0f1"}
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/computehub_video.mp4"
STYLE = sys.argv[3] if len(sys.argv) > 3 else "tech"

BG = STYLE_COLOR.get(STYLE, "black")
FG = STYLE_TEXT.get(STYLE, "white")
W, H = 720, 1280

# 生成示例文案
script = f"今天我们来聊聊：{TOPIC}。这是一个全新的时代，技术正在以惊人的速度改变着世界。让我们一起拥抱变化，创造未来。感谢您的观看。"

# 1. TTS
print(json.dumps({"step": "tts", "status": "started", "text_len": len(script)}))
tts = gTTS(text=script, lang="zh-cn", slow=False)
audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
tts.save(audio)
dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", audio],
    capture_output=True, text=True
).stdout.strip() or 8)
print(json.dumps({"step": "tts", "status": "done", "duration": dur}))

# 2. 分行
lines = textwrap.wrap(script, width=14) or [script]

# 3. 合成视频 - 使用多个 drawtext 叠加
drawtexts = []
for i, line in enumerate(lines):
    y_pos = int(H * 0.3 + i * 60)
    start = i * dur / len(lines)
    end = (i + 1) * dur / len(lines) if i < len(lines) - 1 else dur
    escaped = line.replace("'", "\\'").replace(":", "\\:")
    drawtexts.append(
        f"drawtext=text='{escaped}'"
        f":fontcolor={FG}:fontsize=36"
        f":x=(w-text_w)/2:y={y_pos}"
        f":enable='between(t,{start},{end})'"
    )

vf = f"color=c={BG}:s={W}x{H}:d={dur}[bg];[bg]{','.join(drawtexts)}[vid]"

print(json.dumps({"step": "render", "status": "started", "lines": len(lines), "duration": dur}))

cmd = [
    "ffmpeg", "-y",
    "-i", audio,
    "-filter_complex", vf,
    "-map", "[vid]", "-map", "0:a",
    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
    "-c:a", "aac", "-shortest",
    OUTPUT
]

r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
os.unlink(audio)

if r.returncode != 0:
    print(json.dumps({"step": "render", "status": "failed", "error": r.stderr[-300:]}))
    sys.exit(1)

size = os.path.getsize(OUTPUT) / (1024*1024)
print(json.dumps({"step": "done", "output": OUTPUT, "size_mb": round(size, 1), "duration_sec": round(dur, 1)}))
'''

# ====== 封装脚本 ======
WRAPPER = f'''#!/data/data/com.termux/files/usr/bin/bash
# ComputeHub 视频生产包装器
set -e
cd /tmp
cat > /tmp/video_pipeline.py << 'PYEOF'
{PIPELINE_SCRIPT}
PYEOF
python3 /tmp/video_pipeline.py "$@"
rm -f /tmp/video_pipeline.py
'''


def submit_video_task(gateway_url, topic, output_path="/tmp/computehub_video.mp4", style="tech"):
    """通过 Gateway API 提交视频生产任务"""
    import urllib.request
    import urllib.error

    # base64 包装脚本
    encoded = base64.b64encode(WRAPPER.encode()).decode()

    payload = json.dumps({
        "node_id": "redmi-1",
        "command": f"echo {encoded} | base64 -d | bash -s '{topic}' '{output_path}' '{style}'",
        "timeout": 180
    }).encode()

    req = urllib.request.Request(
        f"{gateway_url}/api/v1/tasks/submit",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def get_task_result(gateway_url, task_id):
    """轮询任务结果"""
    import urllib.request
    import time

    for i in range(30):
        try:
            req = urllib.request.Request(
                f"{gateway_url}/api/v1/tasks/progress?task_id={task_id}"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                result = data.get("data", {})
                if result.get("running") == False or result.get("running") == None:
                    return result
        except Exception as e:
            return {"error": str(e)}
        time.sleep(2)
    return {"error": "timeout"}


if __name__ == "__main__":
    gw = os.environ.get("GATEWAY", "http://192.168.1.12:8282")
    topic = sys.argv[1] if len(sys.argv) > 1 else "AI改变生活"
    output = sys.argv[2] if len(sys.argv) > 2 else "/tmp/computehub_video.mp4"
    style = sys.argv[3] if len(sys.argv) > 3 else "tech"

    print(f"🚀 提交视频任务 → {gw}")
    print(f"   主题: {topic}")
    print(f"   输出: {output}")
    print(f"   风格: {style}")

    result = submit_video_task(gw, topic, output, style)
    print(f"📤 提交结果: {json.dumps(result, indent=2)}")

    if "data" in result and "task_id" in result["data"]:
        task_id = result["data"]["task_id"]
        print(f"\n⏳ 等待任务完成 (task_id={task_id})...")
        output_result = get_task_result(gw, task_id)
        stdout = output_result.get("stdout", "")
        stderr = output_result.get("stderr", "")
        
        print(f"\n📋 任务结果:")
        print(f"   exit_code: {output_result.get('exit_code')}")
        print(f"   duration: {output_result.get('duration')}")
        
        if stdout:
            print(f"   stdout:\n{stdout}")
        if stderr:
            print(f"   stderr:\n{stderr[:500]}")
    else:
        print(f"\n❌ 提交失败")
