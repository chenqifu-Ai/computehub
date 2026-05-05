#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送SSH配置文档到邮箱
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'smtp_port': 465,
    'sender_email': '19525456@qq.com',
    'sender_password': 'ormxhluuafwnbgei',
    'receiver_email': '19525456@qq.com'
}

def read_document():
    """读取文档内容"""
    with open('/root/.openclaw/workspace/docs/ssh_key_setup_complete.md', 'r', encoding='utf-8') as f:
        return f.read()

def send_email(subject, content):
    """发送邮件"""
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['receiver_email']
        msg['Subject'] = subject
        
        # 添加文本内容
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # 连接SMTP服务器并发送
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
            
        print("✅ 邮件发送成功!")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    """主函数"""
    print("📧 发送SSH配置文档...")
    
    # 读取文档
    document_content = read_document()
    
    # 发送邮件
    subject = "🔐 SSH密钥认证配置完整文档 - 2026-04-07"
    email_sent = send_email(subject, document_content)
    
    if email_sent:
        print("🎯 文档已发送到邮箱: 19525456@qq.com")
        print("📋 请查收完整配置文档")
    else:
        print("⚠️ 邮件发送失败，文档位置:")
        print("   /root/.openclaw/workspace/docs/ssh_key_setup_complete.md")

if __name__ == "__main__":
    main()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
