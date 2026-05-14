#!/usr/bin/env python3
"""发送 ComputeHub 局域网下载命令到邮箱"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.header import Header

# SMTP 配置（从 daily_report.py 复制）
email_cfg = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "xzxveoguxylbbgbg"
}

body = """\
老大，ComputeHub 局域网下载命令：

▎Gateway (Windows)
curl -sL "http://192.168.1.7:8282/api/v1/download?file=computehub-gateway-windows-amd64.exe" -o computehub-gateway-windows-amd64.exe

▎Worker (Windows)
curl -sL "http://192.168.1.7:8282/api/v1/download?file=computehub-worker-windows-amd64.exe" -o computehub-worker-windows-amd64.exe

▎Gateway (Linux ARM64)
curl -sL "http://192.168.1.7:8282/api/v1/download?file=computehub-gateway-linux-arm64" -o computehub-gateway-linux-arm64
chmod +x computehub-gateway-linux-arm64

▎Worker (Linux ARM64)
curl -sL "http://192.168.1.7:8282/api/v1/download?file=computehub-worker-linux-arm64" -o computehub-worker-linux-arm64
chmod +x computehub-worker-linux-arm64

▎TUI (Linux ARM64)
curl -sL "http://192.168.1.7:8282/api/v1/download?file=computehub-tui-linux-arm64" -o computehub-tui-linux-arm64
chmod +x computehub-tui-linux-arm64

▎Worker 启动命令（Linux ARM64，心跳25秒）
./computehub-worker --gw http://192.168.1.7:8282 --heartbeat 25

-- 小智 🤖
"""

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = Header("📦 ComputeHub 局域网下载命令", "utf-8")
msg["From"] = email_cfg["from_email"]
msg["To"] = email_cfg["to_email"]

ctx = ssl.create_default_context()
with smtplib.SMTP_SSL(email_cfg["smtp_server"], email_cfg["smtp_port"], timeout=15, context=ctx) as server:
    server.login(email_cfg["from_email"], email_cfg["password"])
    server.sendmail(email_cfg["from_email"], [email_cfg["to_email"]], msg.as_string())

print("✅ 邮件已发送")
