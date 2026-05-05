#!/usr/bin/env python3
"""发送模型切换指南PPT邮件"""

from scripts.email_utils import send_email_safe
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
    subject = "【小智指南】OpenClaw模型切换操作手册"
    
    content = """
老大，

小智已完成《OpenClaw模型切换指南》PPT制作。

这份指南包含：
1. 模型切换概述（为什么需要切换）
2. 本地 vs 云端 对比分析
3. 配置文件说明和参数格式
4. 详细切换操作步骤
5. 常见问题解答

关键提醒：
- 在家用本地模型（响应快、零费用）
- 外出用云端模型（随时可用、稳定）

切换方法：直接对我说"切换到本地模型"或"切换到云端模型"

请用浏览器打开附件查看精美PPT。

此致
小智
"""
    
    html_content = """
    <html>
    <body style="font-family: 'Microsoft YaHei', sans-serif; padding: 20px; background: #0f172a; color: #e2e8f0;">
        <div style="max-width: 600px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 15px;">
            <h2 style="color: #22d3ee; border-bottom: 2px solid #22d3ee; padding-bottom: 10px;">OpenClaw 模型切换指南</h2>
            <p style="color: #94a3b8;">老大，</p>
            <p style="color: #e2e8f0;">小智已完成模型切换操作手册PPT制作。</p>
            
            <div style="background: rgba(34,211,238,0.1); padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #22d3ee; margin-bottom: 15px;">指南内容</h3>
                <ul style="color: #94a3b8; line-height: 2;">
                    <li>模型切换概述</li>
                    <li>本地 vs 云端 对比</li>
                    <li>配置文件说明</li>
                    <li>切换操作步骤</li>
                    <li>常见问题解答</li>
                </ul>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0;">
                <div style="background: linear-gradient(135deg, #065f46, #047857); padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="color: white; font-weight: bold; margin-bottom: 10px;">🏠 本地模型</div>
                    <div style="color: rgba(255,255,255,0.8); font-size: 14px;">响应快、零费用</div>
                </div>
                <div style="background: linear-gradient(135deg, #1e40af, #3b82f6); padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="color: white; font-weight: bold; margin-bottom: 10px;">☁️ 云端模型</div>
                    <div style="color: rgba(255,255,255,0.8); font-size: 14px;">随时可用、稳定</div>
                </div>
            </div>
            
            <p style="color: #22d3ee; font-size: 18px;">切换方法：直接对我说"切换到本地模型"或"切换到云端模型"</p>
            
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
    
    attachment_path = "/root/.openclaw/workspace/output/model-switch-guide.html"
    if os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', 
                                 filename='OpenClaw模型切换指南.html')
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

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
