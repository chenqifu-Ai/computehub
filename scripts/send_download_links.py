#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送 ComputeHub v0.7.6 各平台下载链接到邮箱"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'smtp_port': 465,
    'sender_email': '19525456@qq.com',
    'sender_password': 'ormxhluuafwnbgei',
    'receiver_email': '19525456@qq.com'
}

GW = "http://192.168.1.17:8282"

CONTENT = f"""ComputeHub v0.7.6 各平台下载链接
===============================================
网关地址: {GW}

━━ 各平台直接下载 ━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Linux AMD64（服务器/PC）
   下载: {GW}/api/v1/download?file=computehub&platform=linux-amd64
   命令: curl -sL "{GW}/api/v1/download?file=computehub&platform=linux-amd64" -o computehub && chmod +x computehub

2️⃣ Linux ARM64（树莓派/ARM服务器）
   下载: {GW}/api/v1/download?file=computehub&platform=linux-arm64
   命令: curl -sL "{GW}/api/v1/download?file=computehub&platform=linux-arm64" -o computehub && chmod +x computehub

3️⃣ macOS Intel
   下载: {GW}/api/v1/download?file=computehub&platform=darwin-amd64
   命令: curl -sL "{GW}/api/v1/download?file=computehub&platform=darwin-amd64" -o computehub && chmod +x computehub

4️⃣ macOS Apple Silicon (M1/M2/M3/M4)
   下载: {GW}/api/v1/download?file=computehub&platform=darwin-arm64
   命令: curl -sL "{GW}/api/v1/download?file=computehub&platform=darwin-arm64" -o computehub && chmod +x computehub

5️⃣ Windows AMD64
   下载: {GW}/api/v1/download?file=computehub.exe&platform=windows-amd64
   命令: curl -sL "{GW}/api/v1/download?file=computehub.exe&platform=windows-amd64" -o computehub.exe

━━ 用法 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

下载后运行:
  ./computehub version           # 查看版本
  ./computehub gateway --port 8282 --token <你的token>  # 启动网关
  ./computehub worker --gw http://<网关IP>:8282        # 启动工作节点
  ./computehub tui --gw http://<网关IP>:8282            # 启动终端界面

━━ 参数说明 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ?file=computehub         → Linux/macOS 三合一二进制
  ?file=computehub.exe     → Windows 三合一二进制
  &platform=linux-amd64    → 指定平台（必填，否则返回默认arm64）

  支持的 platform 值：linux-amd64, linux-arm64, darwin-amd64, darwin-arm64, windows-amd64

━━ 编译信息 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  版本: v0.7.6
  编译器: Go, CGO_ENABLED=0
  大小: ~7-11MB 各平台
"""

def send_email():
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['receiver_email']
        msg['Subject'] = '📦 ComputeHub v0.7.6 各平台下载链接'
        msg.attach(MIMEText(CONTENT, 'plain', 'utf-8'))

        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)

        print("✅ 邮件发送成功!")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == '__main__':
    send_email()
