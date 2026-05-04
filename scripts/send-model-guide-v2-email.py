#!/usr/bin/env python3
"""发送模型切换指南PPT邮件（含踩坑记录）"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_ACCOUNT = "19525456@qq.com"
AUTH_CODE = "xunlwhjokescbgdd"

def send_email():
    to_addr = "19525456@qq.com"
    subject = "【小智指南】OpenClaw模型切换操作手册（含踩坑记录）"
    
    content = """
老大，

小智已更新《OpenClaw模型切换指南》，增加了踩坑记录。

这次踩的坑：
1. 本地没有 glm-5 模型（只有 llama3, phi3, deepseek-coder）
2. 混淆了本地和云端模型格式
3. 忘记检查本地服务器状态

已修正的内容：
- 正确的模型格式：本地 ollama/xxx，云端 ollama-cloud/xxx
- 先查看本地可用模型再切换
- 服务器信息速查表

请用浏览器打开附件查看更新后的PPT。

此致
小智
"""
    
    html_content = """
    <html>
    <body style="font-family: 'Microsoft YaHei', sans-serif; padding: 20px; background: #0f172a; color: #e2e8f0;">
        <div style="max-width: 600px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 15px;">
            <h2 style="color: #22d3ee; border-bottom: 2px solid #22d3ee; padding-bottom: 10px;">OpenClaw 模型切换指南（更新版）</h2>
            <p style="color: #94a3b8;">老大，</p>
            <p style="color: #e2e8f0;">小智已更新模型切换指南，增加了踩坑记录。</p>
            
            <div style="background: rgba(239,68,68,0.1); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #ef4444;">
                <h3 style="color: #ef4444; margin-bottom: 15px;">⚠️ 这次踩的坑</h3>
                <ul style="color: #94a3b8; line-height: 2;">
                    <li>本地没有 glm-5 模型（只有 llama3, phi3, deepseek-coder）</li>
                    <li>混淆了本地和云端模型格式</li>
                    <li>忘记检查本地服务器状态</li>
                </ul>
            </div>
            
            <div style="background: rgba(34,197,94,0.1); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #22c55e;">
                <h3 style="color: #22c55e; margin-bottom: 15px;">✅ 已修正</h3>
                <ul style="color: #94a3b8; line-height: 2;">
                    <li>正确的模型格式：<br><code style="background: #334155; padding: 2px 8px; border-radius: 4px;">本地 ollama/xxx</code> vs <code style="background: #334155; padding: 2px 8px; border-radius: 4px;">云端 ollama-cloud/xxx</code></li>
                    <li>先查看本地可用模型再切换</li>
                    <li>服务器信息速查表</li>
                </ul>
            </div>
            
            <hr style="margin: 25px 0; border-color: #334155;">
            <p style="color: #64748b; font-size: 14px;">
                小智 · AI助手<br>
                2026年3月21日
            </p>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = to_addr
    msg['Subject'] = subject
    
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    attachment_path = "/root/.openclaw/workspace/output/model-switch-guide-v2.html"
    if os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', 
                                 filename='OpenClaw模型切换指南-v2.html')
            msg.attach(attachment)
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ACCOUNT, AUTH_CODE)
            server.sendmail(EMAIL_ACCOUNT, to_addr, msg.as_string())
        print("邮件发送成功！")
        return True
    except Exception as e:
        print(f"邮件发送失败：{e}")
        return False

if __name__ == "__main__":
    send_email()