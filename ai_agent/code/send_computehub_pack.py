#!/usr/bin/env python3
"""发送 ComputeHub 打包文件到 QQ 邮箱"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

CONFIG_PATH = "/root/.openclaw/workspace/config/email.conf"
config = {}
with open(CONFIG_PATH) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip()

SENDER_EMAIL = config.get('EMAIL', '19525456@qq.com')
EMAIL_PASS = config.get('AUTH_CODE', '')
RECEIVER_EMAIL = "19525456@qq.com"

ATTACHMENT = "/root/.openclaw/workspace/ai_agent/results/computehub-v0.7.6.tar.gz"

def main():
    if not os.path.exists(ATTACHMENT):
        print(f"❌ 文件不存在: {ATTACHMENT}")
        return
    
    size = os.path.getsize(ATTACHMENT) / 1024 / 1024
    print(f"📧 准备发送邮件 → {RECEIVER_EMAIL}")
    print(f"📎 附件: computehub-v0.7.6.tar.gz ({size:.1f}MB)")
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = "【ComputeHub v0.7.6】工程源码包 - 2026-05-13"
    
    body = f"""
<html>
<body style="font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; color: #333; line-height: 1.8;">
<h2>📦 ComputeHub v0.7.6 工程源码包</h2>
<p>老大，ComputeHub v0.7.6 全平台编译完成（15/15 ✅），源码包已打包，请查收。</p>

<h3>📋 内容清单</h3>
<ul>
    <li>✅ 完整源码（cmd/、src/）</li>
    <li>✅ 配置文件（config/、go.mod、go.sum）</li>
    <li>✅ 文档（docs/、*.md）</li>
    <li>✅ 脚本（scripts/）</li>
    <li>✅ Docker 配置</li>
</ul>

<h3>📊 版本信息</h3>
<ul>
    <li><strong>版本</strong>: v0.7.6</li>
    <li><strong>编译平台</strong>: linux-amd64, linux-arm64, darwin-amd64, darwin-arm64, windows-amd64</li>
    <li><strong>编译结果</strong>: 15/15 全部通过 ✅</li>
    <li><strong>安装包大小</strong>: {size:.1f}MB（排除了二进制/日志/大文件）</li>
</ul>

<h3>🔗 仓库地址</h3>
<p><a href="https://github.com/chenqifu-Ai/computehub">https://github.com/chenqifu-Ai/computehub</a></p>

<p>详细优化分析之前已单独发送过邮件。有问题随时找我 😊</p>

<p style="color:#999;font-size:12px;">— 小智 AI 助手 | 2026-05-13 09:45</p>
</body>
</html>
"""
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    
    # 附件
    with open(ATTACHMENT, "rb") as f:
        attach = MIMEBase('application', 'octet-stream')
        attach.set_payload(f.read())
    encoders.encode_base64(attach)
    attach.add_header('Content-Disposition', 'attachment', filename="computehub-v0.7.6.tar.gz")
    msg.attach(attach)
    
    # 发送
    try:
        if config.get('SMTP_PORT', '465') == '465':
            server = smtplib.SMTP_SSL(config.get('SMTP_SERVER', 'smtp.qq.com'), 465, timeout=30)
        else:
            server = smtplib.SMTP(config.get('SMTP_SERVER', 'smtp.qq.com'), int(config.get('SMTP_PORT', '25')), timeout=30)
            server.starttls()
        
        server.login(SENDER_EMAIL, EMAIL_PASS)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == '__main__':
    main()
