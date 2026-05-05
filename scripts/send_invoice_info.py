#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送开票资料到邮箱
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "xunlwhjokescbgdd"
}

# 开票资料
INVOICE_INFO = {
    "company_name": "中物（厦门）数字技术有限责任公司",
    "tax_id": "91350200MAENGMDR4W",
    "address": "厦门火炬高新区新科广场 2 号楼坂上社 37-2 号 306-2B 室",
    "phone": "15960822790",
    "bank_name": "中国民生银行前埔支行",
    "bank_account": "654880111"
}

def send_invoice_email():
    """发送开票资料邮件"""
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    subject = f"📋 公司开票资料 - {today}"
    
    # HTML 内容
    html_content = f"""
<html>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        
        <!-- 标题 -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 24px;">📋 公司开票资料</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{today}</p>
        </div>
        
        <!-- 开票信息 -->
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 15px 0; color: #2d3436; font-size: 18px;">📄 开票信息</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; width: 120px;"><strong>单位名称</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{INVOICE_INFO['company_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>纳税识别号</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{INVOICE_INFO['tax_id']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>单位地址</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{INVOICE_INFO['address']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>联系电话</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{INVOICE_INFO['phone']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>开户银行</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{INVOICE_INFO['bank_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>银行账号</strong></td>
                    <td style="padding: 10px;">{INVOICE_INFO['bank_account']}</td>
                </tr>
            </table>
        </div>
        
        <!-- 纯文本版本 -->
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
            <h3 style="margin: 0 0 10px 0; color: #856404; font-size: 16px;">📝 复制专用（纯文本）</h3>
            <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word; color: #856404; font-size: 13px;">
单位名称：{INVOICE_INFO['company_name']}
纳税识别号：{INVOICE_INFO['tax_id']}
单位地址：{INVOICE_INFO['address']}
联系电话：{INVOICE_INFO['phone']}
开户银行：{INVOICE_INFO['bank_name']}
银行账号：{INVOICE_INFO['bank_account']}
            </pre>
        </div>
        
        <!-- 提示 -->
        <div style="background: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0; color: #004085; font-size: 14px;">
                <strong>💡 提示:</strong>
                <br>- 开票时请核对以上信息
                <br>- 纳税识别号请务必准确
                <br>- 银行账号用于退款/转账
            </p>
        </div>
        
        <!-- 底部 -->
        <div style="border-top: 2px solid #dee2e6; padding-top: 15px; margin-top: 20px; color: #6c757d; font-size: 12px; text-align: center;">
            <p style="margin: 0;">🤖 开票资料由系统自动发送</p>
            <p style="margin: 5px 0 0 0;">📧 如有疑问请联系</p>
        </div>
        
    </div>
</body>
</html>
"""
    
    # 纯文本内容
    text_content = f"""
📋 公司开票资料
=====================================
发送时间：{today}

单位名称：{INVOICE_INFO['company_name']}
纳税识别号：{INVOICE_INFO['tax_id']}
单位地址：{INVOICE_INFO['address']}
联系电话：{INVOICE_INFO['phone']}
开户银行：{INVOICE_INFO['bank_name']}
银行账号：{INVOICE_INFO['bank_account']}

=====================================
💡 提示:
- 开票时请核对以上信息
- 纳税识别号请务必准确
- 银行账号用于退款/转账
"""
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_CONFIG["from_email"]
        msg["To"] = EMAIL_CONFIG["to_email"]
        
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.login(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["password"])
        server.sendmail(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["to_email"], msg.as_string())
        server.quit()
        
        print(f"✅ 开票资料已发送到 {EMAIL_CONFIG['to_email']}")
        print(f"   主题：{subject}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

if __name__ == "__main__":
    send_invoice_email()


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
