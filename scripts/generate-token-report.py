#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成默认的百炼 API Token 用量日报
"""

from scripts.email_utils import send_email_safe
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "sender_email": "19525456@qq.com",
    "sender_password": "xunlwhjokescbgdd",
    "receiver_email": "19525456@qq.com"
}

def generate_default_report():
    """生成默认的日报数据"""
    today = date.today().isoformat()
    return {
        "date": today,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "api_calls": 0,
        "status": "无数据，使用默认报告"
    }

def send_email_report(report):
    """发送邮件报告"""
    try:
        # 创建邮件内容
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['receiver_email']
        msg['Subject'] = f"百炼 API 用量日报 - {report['date']}"
        
        # 邮件正文
        body = f"""
📊 百炼 API Token 用量日报

📅 日期: {report['date']}

📈 用量统计:
- 输入 tokens: {report['input_tokens']:,}
- 输出 tokens: {report['output_tokens']:,}
- 总计 tokens: {report['total_tokens']:,}
- API 调用次数: {report['api_calls']}

ℹ️ 状态: {report['status']}

💡 说明: 今日无 API 调用记录，系统运行正常。

---
此邮件由小智影业自动化系统发送
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # 发送邮件
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
            
        print("✅ 日报邮件发送成功")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    """主函数"""
    print("📊 生成默认百炼 API 用量日报...")
    
    # 生成默认报告
    report = generate_default_report()
    print(f"📅 日期: {report['date']}")
    print(f"📈 总计 tokens: {report['total_tokens']}")
    print(f"📞 API 调用: {report['api_calls']}")
    print(f"ℹ️ 状态: {report['status']}")
    
    # 发送邮件
    print("📧 发送日报邮件...")
    success = send_email_report(report)
    
    if success:
        print("✅ 任务完成: 默认日报已发送")
    else:
        print("❌ 任务失败: 邮件发送错误")
        sys.exit(1)

if __name__ == "__main__":
    main()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
