#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单邮件发送脚本
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_simple_email():
    """发送简单邮件"""
    
    # 邮件配置
    smtp_server = "smtp.qq.com"
    smtp_port = 465
    sender_email = "19525456@qq.com"
    auth_code = "xunlwhjokescbgdd"
    receiver_email = "19525456@qq.com"
    
    # 读取SOP内容
    sop_file = "/root/.openclaw/workspace/ai_agent/results/contract_signing_sop.md"
    with open(sop_file, 'r', encoding='utf-8') as f:
        sop_content = f.read()
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "合同签订SOP文档"
    
    # 邮件正文
    body = """老大您好！

这是您要求的合同签订标准操作程序（SOP）文档。

文档包含7个完整阶段的合同签订流程，各部门职责分工明确，每个步骤都有具体操作指引和交付物要求。

请查收附件。

小智
"""
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 添加附件
    attachment = MIMEText(sop_content, 'plain', 'utf-8')
    attachment.add_header('Content-Disposition', 'attachment', filename='contract_sop.md')
    msg.attach(attachment)
    
    try:
        # 发送邮件
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, auth_code)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        
        print("✅ 邮件发送成功！")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = send_simple_email()
    if success:
        print("合同签订SOP已发送到您的邮箱")
    else:
        print("发送失败，请检查配置")

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
