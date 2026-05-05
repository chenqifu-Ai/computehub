#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送当前执行规则到用户邮箱
"""

from scripts.email_utils import send_email_safe
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

def send_rules_email():
    """发送规则邮件"""
    # 读取MEMORY.md中的规则部分
    memory_file = "/root/.openclaw/workspace/MEMORY.md"
    
    with open(memory_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取规则相关部分
    rules_start = content.find("## 📋 默认执行规则（永久记忆")
    if rules_start == -1:
        rules_start = content.find("## 用户偏好")
    
    if rules_start != -1:
        # 找到规则结束位置（下一个大标题或文件末尾）
        next_section = content.find("\n## ", rules_start + 1)
        if next_section == -1:
            rules_content = content[rules_start:]
        else:
            rules_content = content[rules_start:next_section]
    else:
        rules_content = content
    
    # 邮件配置
    smtp_server = "smtp.qq.com"
    smtp_port = 465
    sender_email = "19525456@qq.com"
    auth_code = "xunlwhjokescbgdd"
    receiver_email = "19525456@qq.com"
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = Header('OpenClaw执行规则汇报 - 2026-03-26', 'utf-8')
    
    # 邮件正文
    body = f"""老大您好！

这是您要求的当前OpenClaw执行规则汇报：

{rules_content}

---
此邮件由OpenClaw自动发送
时间：2026-03-26 18:50
"""
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        # 发送邮件
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, auth_code)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        
        print("✅ 邮件发送成功！")
        print(f"📧 收件人: {receiver_email}")
        print("📄 主题: OpenClaw执行规则汇报 - 2026-03-26")
        
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = send_rules_email()
    if not success:
        exit(1)

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
