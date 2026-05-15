#!/usr/bin/env python3
"""发送 ComputeHub Gallery + Worker 自动回传 使用说明邮件"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os, sys

# 从配置读取
config_path = os.path.expanduser('~/.openclaw/workspace/config/email.conf')
with open(config_path) as f:
    config = dict(line.strip().split('=') for line in f if '=' in line)

SMTP_SERVER = config.get('SMTP_SERVER', 'smtp.qq.com')
SMTP_PORT = int(config.get('SMTP_PORT', 465))
SENDER = config.get('EMAIL', '19525456@qq.com')
PASS = config.get('AUTH_CODE', '')
RECEIVER = '19525456@qq.com'

COMMIT_LOG = """8ac1209a fix: version.go 用 const 定义（grep 匹配 fix）
ad4a7bb7 feat: 作品广场 Gallery + Worker 自动回传 (v0.7.7)
4acdd979 chore: v0.7.6 全平台重编译 + gatekeeper download 端点"""

def build_html():
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; line-height: 1.7; color: #333; max-width: 700px; margin: auto; padding: 20px; }
        h1 { color: #f7971e; border-left: 4px solid #f7971e; padding-left: 14px; }
        h2 { color: #302b63; margin-top: 28px; }
        .tag { display: inline-block; background: #f7971e; color: #fff; padding: 3px 10px; border-radius: 4px; font-size: 13px; }
        pre { background: #f5f5f5; padding: 14px; border-radius: 6px; overflow-x: auto; font-size: 13px; }
        code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
        .box { background: #fff8e8; border: 1px solid #f0d08a; border-radius: 8px; padding: 16px 20px; margin: 16px 0; }
        .box.green { background: #e8f8e8; border-color: #8ac08a; }
        table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        th, td { border: 1px solid #ddd; padding: 10px 14px; text-align: left; }
        th { background: #302b63; color: #fff; }
        hr { border: none; border-top: 1px solid #eee; margin: 30px 0; }
    </style>
</head>
<body>

<h1>🎬 小智影业 · 作品广场 Gallery 功能上线</h1>
<p style="color:#888;">ComputeHub v0.7.7 · 2026-05-15</p>

<div class="box">
<strong>✅ 方案B完成</strong> — 改了 2 个文件，实现 Worker 自动回传 + Gallery 手动/自动上传
</div>

<h2>📦 改动内容</h2>

<h3>1️⃣ Gallery 上传接口 <code>src/gateway/gallery.go</code></h3>
<ul>
    <li>新增 <code>POST /api/v1/gallery/upload</code> — 接收 <code>multipart/form-data</code> 文件</li>
    <li>上传文件存入 <code>/var/computehub/gallery/</code>，同名自动加时间戳</li>
    <li>限制 500MB，带路径安全检查</li>
    <li>HTML 页面自带拖拽上传区域，浏览器拖文件即传</li>
</ul>

<h3>2️⃣ Worker 自动回传 <code>cmd/worker/main.go</code></h3>
<ul>
    <li>新增 <code>--upload-dir &lt;目录&gt;</code> 参数</li>
    <li>任务成功后自动扫描目录，找到 <code>.mp4/.mp3/.jpg</code> 等媒体文件</li>
    <li>自动 POST 到 Gateway 的 upload 端点</li>
    <li>完全无需手动操作：Worker 执行完任务 → 扫描目录 → 上传文件 → Gallery 自动显示</li>
</ul>

<hr>

<h2>🚀 使用方法</h2>

<div class="box green">
<strong>启动 Worker（带上传目录）：</strong>
<pre>./compute-worker --upload-dir /path/to/output --gw http://192.168.1.7:8282</pre>
</div>

<p>然后提交视频/音频生成任务，Worker 执行完自动把结果文件传回来。</p>

<div class="box green">
<strong>访问 Gallery 页面：</strong><br>
<code>http://192.168.1.7:8282/api/v1/gallery</code>
</div>

<p>支持拖拽手动上传、在线播放、下载。<br>
Worker 自动上传的媒体文件也会实时出现在 Gallery 中。</p>

<hr>

<h2>📋 完整配置示例</h2>

<pre># Worker 启动（带自动回传）
./compute-worker \\
  --gw http://192.168.1.7:8282 \\
  --node-name worker-localhost \\
  --upload-dir /output \\
  --report-dir ./reports

# 提交任务（生成视频后自动回传）
python3 submit_task.py \\
  --cmd "ffmpeg -f lavfi -i color=c=red:s=1280x720:d=10 output.mp4" \\
  --gw http://192.168.1.7:8282
</pre>

<h2>🏗 路由一览</h2>
<table>
    <tr><th>路径</th><th>说明</th></tr>
    <tr><td><code>GET /api/v1/gallery</code></td><td>作品广场页面 (HTML) / JSON 接口</td></tr>
    <tr><td><code>POST /api/v1/gallery/upload</code></td><td>文件上传 (multipart/form-data)</td></tr>
    <tr><td><code>GET /api/v1/files/&lt;文件名&gt;</code></td><td>文件下载/预览</td></tr>
</table>

<h2>🔄 工作流程</h2>
<ol>
    <li>用户提交任务到 Gateway</li>
    <li>Worker 拉取任务，执行命令（如 FFmpeg 生成视频）</li>
    <li>任务完成后，Worker 扫描 <code>--upload-dir</code> 目录</li>
    <li>找到媒体文件 → POST 到 Gateway <code>/upload</code> 端点</li>
    <li>Gallery 刷新，新作品出现在页面上</li>
    <li>用户可在浏览器直接播放/下载</li>
</ol>

<hr>

<h2>🔧 技术细节</h2>
<table>
    <tr><th>项</th><th>值</th></tr>
    <tr><td>版本</td><td>v0.7.7</td></tr>
    <tr><td>最近提交</td><td><code>ad4a7bb7</code></td></tr>
    <tr><td>分支</td><td>master</td></tr>
    <tr><td>存储目录</td><td><code>/var/computehub/gallery/</code></td></tr>
    <tr><td>上限大小</td><td>500MB/文件</td></tr>
    <tr><td>支持格式</td><td>mp4/webm/mov/avi/mkv/mp3/wav/jpg/png/gif 等</td></tr>
    <tr><td>认证方式</td><td>Worker 通过 Gateway Token 验证</td></tr>
</table>

<p style="color:#999;font-size:12px;margin-top:40px;">
— 小智 AI 助手 · ComputeHub v0.7.7 · 2026-05-15
</p>

</body>
</html>"""

def main():
    if not PASS:
        print("❌ 未配置邮箱授权码，请检查 email.conf")
        sys.exit(1)

    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER
    msg['To'] = RECEIVER
    msg['Subject'] = "🎬 [小智] ComputeHub v0.7.7 作品广场 Gallery + Worker自动回传 使用说明"

    html = build_html()
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()

        server.login(SENDER, PASS)
        server.sendmail(SENDER, RECEIVER, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功!")
        print(f"   发件人: {SENDER}")
        print(f"   收件人: {RECEIVER}")
        print(f"   主题: ComputeHub v0.7.7 Gallery + Worker自动回传 使用说明")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP 认证失败 — QQ 邮箱授权码可能已过期，请重新生成")
        return False
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

if __name__ == "__main__":
    main()
