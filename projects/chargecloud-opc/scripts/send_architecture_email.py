#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChargeCloud OPC 架构图邮件发送器
发送 HTML 格式的架构图到老大邮箱

创建时间：2026-04-19
作者：小智 (数据智能体)
"""

from scripts.email_utils import send_email_safe
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# 邮箱配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SENDER_EMAIL = "19525456@qq.com"
SENDER_PASSWORD = "ormxhluuafwnbgei"  # QQ 邮箱授权码
RECEIVER_EMAIL = "19525456@qq.com"

# 文件路径
HTML_FILE = "/root/.openclaw/workspace/projects/chargecloud-opc/architecture-images/architecture_email.html"
CONFIG_DIR = "/root/.openclaw/workspace/projects/chargecloud-opc/agents/"

def send_architecture_email():
    """发送架构图邮件"""
    
    print("=" * 60)
    print("ChargeCloud OPC 架构图邮件发送器")
    print("=" * 60)
    print(f"发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"发件人：{SENDER_EMAIL}")
    print(f"收件人：{RECEIVER_EMAIL}")
    print()
    
    # 读取 HTML 内容
    print("📄 读取 HTML 邮件内容...")
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    print(f"✅ HTML 内容大小：{len(html_content):,} bytes")
    
    # 创建邮件
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🤖 ChargeCloud OPC - AI 智能体架构图 (v1.0) - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    
    # 添加 HTML 内容
    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)
    
    # 附加配置文件 (可选)
    config_files = [
        'CONFIG_OVERVIEW.md',
        'ceo_agent/config.yaml',
        'marketing_agent/config.yaml',
        'operations_agent/config.yaml',
        'finance_agent/config.yaml',
        'data_agent/config.yaml',
        'risk_agent/config.yaml',
    ]
    
    print("\n📎 准备附加配置文件...")
    for config_file in config_files:
        file_path = os.path.join(CONFIG_DIR, config_file)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(config_file)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    msg.attach(part)
                print(f"   ✅ {config_file}")
            except Exception as e:
                print(f"   ⚠️ {config_file} 失败：{e}")
        else:
            print(f"   ⚠️ {config_file} 不存在")
    
    # 发送邮件
    print(f"\n📧 正在发送邮件到 {RECEIVER_EMAIL}...")
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        server.quit()
        
        print("\n" + "=" * 60)
        print("✅ 邮件发送成功!")
        print("=" * 60)
        print(f"\n📊 邮件内容:")
        print(f"   主题：ChargeCloud OPC - AI 智能体架构图 (v1.0)")
        print(f"   收件人：{RECEIVER_EMAIL}")
        print(f"   附件：{len(config_files)} 个配置文件")
        print(f"\n🎉 老大请注意查收邮件！")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 邮件发送失败!")
        print("=" * 60)
        print(f"错误信息：{e}")
        print("\n可能的原因:")
        print("1. 邮箱授权码过期或错误")
        print("2. SMTP 服务器连接问题")
        print("3. 网络问题")
        print("\n建议:")
        print("- 检查邮箱授权码是否正确")
        print("- 检查网络连接")
        print("- 稍后重试")
        
        return False

if __name__ == '__main__':
    success = send_architecture_email()
    exit(0 if success else 1)


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
