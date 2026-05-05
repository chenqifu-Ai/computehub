#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送合同签订SOP邮件脚本
"""

from scripts.email_utils import send_email_safe
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

def send_contract_sop_email():
    """发送合同签订SOP邮件"""
    
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
    msg['From'] = Header("小智 <19525456@qq.com>", 'utf-8')
    msg['To'] = Header("老大 <19525456@qq.com>", 'utf-8')
    msg['Subject'] = Header("【合同签订SOP】标准操作程序文档", 'utf-8')
    
    # 邮件正文
    body = f"""老大您好！

这是您要求的合同签订标准操作程序（SOP）文档，已按要求制作完成。

主要内容包括：
• 7个完整阶段的合同签订流程
• 各部门职责分工明确
• 每个步骤的具体操作指引和交付物要求
• 关键质量控制点和风险防范措施

请查收附件中的完整SOP文档，如有任何修改需求，请随时告知！

小智
"""
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 添加SOP内容作为附件
    attachment = MIMEText(sop_content, 'plain', 'utf-8')
    attachment.add_header('Content-Disposition', 'attachment', filename="合同签订标准操作程序_SOP-CONTRACT-001.md")
    msg.attach(attachment)
    
    try:
        # 发送邮件
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, auth_code)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        
        print("✅ 邮件发送成功！")
        print(f"📧 收件人: {receiver_email}")
        print("📎 附件: 合同签订标准操作程序_SOP-CONTRACT-001.md")
        print("📋 主题: 【合同签订SOP】标准操作程序文档")
        
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = send_contract_sop_email()
    if success:
        print("\n🎉 任务完成！合同签订SOP已成功发送到您的邮箱。")
    else:
        print("\n⚠️  任务失败！请检查邮件配置或网络连接。")

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
