#!/usr/bin/env python3
"""
邮件发送脚本：发送AI智能体报告
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import json
import os
from datetime import datetime

# 配置
CONFIG = {
    "SMTP_SERVER": "smtp.qq.com",
    "SMTP_PORT": 465,
    "EMAIL": "19525456@qq.com",
    "AUTH_CODE": "xunlwhjokescbgdd",
    "RECIPIENT": "19525456@qq.com"
}

def send_email(subject, body, attachment_path=None):
    """发送邮件"""
    try:
        msg = MIMEMultipart()
        msg['From'] = CONFIG["EMAIL"]
        msg['To'] = Header("老大", "utf-8")
        msg['Subject'] = Header(subject, "utf-8")
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        if attachment_path:
            with open(attachment_path, 'rb') as f:
                part = MIMEText(f.read(), 'base64', 'utf-8')
                part.add_header('Content-Disposition', 
                    'attachment', 
                    filename=os.path.basename(attachment_path))
                msg.attach(part)
        
        server = smtplib.SMTP_SSL(CONFIG["SMTP_SERVER"], CONFIG["SMTP_PORT"])
        server.login(CONFIG["EMAIL"], CONFIG["AUTH_CODE"])
        server.sendmail(CONFIG["EMAIL"], CONFIG["RECIPIENT"], msg.as_string())
        server.quit()
        print("邮件发送成功!")
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False

def generate_report_content(report_file):
    """生成邮件正文"""
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    subject = report_data.get('结论', {}).get('问题', '未知问题')
    content = f"""
小智助手决策报告
======================

问题描述：{report_data.get('结论', {}).get('问题', '')}

最终结论：{report_data.get('结论', {}).get('最佳方案', '')}

详细步骤：
"""
    for i, step in enumerate(report_data.get('结论', {}).get('步骤', []), 1):
        content += f"{i}. {step}\n"
    
    content += f"\n逻辑基础：{', '.join(report_data.get('结论', {}).get('逻辑基础', []))}"
    
    return content

def main():
    """主函数"""
    print("准备发送邮件...")
    
    # 指定要发送的报告文件
    report_file = "/root/.openclaw/workspace/ai_agent/results/wash_car_decision_logical_20260325.json"
    
    if not os.path.exists(report_file):
        print(f"报告文件不存在: {report_file}")
        return
    
    # 生成邮件内容
    subject = "小智洗车决策报告"
    body = generate_report_content(report_file)
    
    # 发送邮件
    success = send_email(subject, body, report_file)
    
    if success:
        print(f"报告已发送到邮箱: {CONFIG['RECIPIENT']}")
    else:
        print("发送失败，请检查邮件配置")

if __name__ == "__main__":
    main()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
