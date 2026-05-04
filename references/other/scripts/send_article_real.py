#!/usr/bin/env python3
"""发送记忆翅膀技术文章邮件 - 使用成功模板"""

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

def send_article_email():
    to_addr = "19525456@qq.com"
    subject = "🦅 记忆翅膀：AI智能体的状态快照与自动恢复系统"
    
    # 读取技术文章内容
    article_path = "/root/.openclaw/workspace/记忆翅膀技术文章.md"
    with open(article_path, 'r', encoding='utf-8') as f:
        article_content = f.read()
    
    content = f"""
老大，

小智已完成"记忆翅膀"状态快照系统的技术文章。

技术突破：
✅ AI智能体状态持久化解决方案
✅ 每小时自动快照，多版本管理
✅ 重启自动恢复，零操作要求
✅ 经过测试验证的完整系统

文章包含完整的技术细节、测试数据和商业价值分析。

请查看附件中的技术文章。

此致
小智
"""
    
    html_content = f"""
    <html>
    <body style="font-family: 'Microsoft YaHei', sans-serif; padding: 20px; background: #0f172a; color: #e2e8f0;">
        <div style="max-width: 600px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 15px;">
            <h2 style="color: #22d3ee; border-bottom: 2px solid #22d3ee; padding-bottom: 10px;">🦅 记忆翅膀技术文章</h2>
            <p style="color: #94a3b8;">老大，</p>
            <p style="color: #e2e8f0;">小智已完成"记忆翅膀"状态快照系统的技术文章。</p>
            
            <div style="background: rgba(34,211,238,0.1); padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #22d3ee; margin-bottom: 15px;">技术突破</h3>
                <ul style="color: #94a3b8; line-height: 2;">
                    <li>✅ AI智能体状态持久化解决方案</li>
                    <li>✅ 每小时自动快照，多版本管理</li>
                    <li>✅ 重启自动恢复，零操作要求</li>
                    <li>✅ 经过测试验证的完整系统</li>
                </ul>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0;">
                <div style="background: linear-gradient(135deg, #065f46, #047857); padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="color: white; font-weight: bold; margin-bottom: 10px;">📸 自动快照</div>
                    <div style="color: rgba(255,255,255,0.8); font-size: 14px;">每小时自动保存状态</div>
                </div>
                <div style="background: linear-gradient(135deg, #1e40af, #3b82f6); padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="color: white; font-weight: bold; margin-bottom: 10px;">🔄 自动恢复</div>
                    <div style="color: rgba(255,255,255,0.8); font-size: 14px;">重启后无缝衔接</div>
                </div>
            </div>
            
            <p style="color: #22d3ee; font-size: 18px;">文章包含完整技术细节和商业价值分析</p>
            
            <hr style="margin: 25px 0; border-color: #334155;">
            <p style="color: #64748b; font-size: 14px;">
                小智 · AI助手<br>
                2026年3月28日
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
    
    # 添加技术文章附件
    if os.path.exists(article_path):
        with open(article_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', 
                                 filename='记忆翅膀技术文章.md')
            msg.attach(attachment)
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ACCOUNT, AUTH_CODE)
            server.sendmail(EMAIL_ACCOUNT, to_addr, msg.as_string())
        print("✅ 技术文章邮件发送成功！")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

if __name__ == "__main__":
    print("🚀 使用成功模板发送技术文章...")
    success = send_article_email()
    if success:
        print("🎉 邮件已发送到 19525456@qq.com")
    else:
        print("⚠️  发送失败，请检查网络或配置")