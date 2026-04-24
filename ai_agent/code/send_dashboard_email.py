#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送项目表盘邮件
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

def send_dashboard_email():
    """发送项目表盘邮件"""
    
    # 读取邮箱配置
    config_path = "/root/.openclaw/workspace/config/email.conf"
    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
    
    # 邮件配置
    smtp_server = config['SMTP_SERVER']
    smtp_port = int(config['SMTP_PORT'])
    email = config['EMAIL']
    auth_code = config['AUTH_CODE']
    
    # 收件人
    to_email = email  # 发送给自己
    
    # 创建邮件
    msg = MimeMultipart()
    msg['From'] = email
    msg['To'] = to_email
    msg['Subject'] = f"项目状态表盘 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # 邮件正文
    body = f"""
    <html>
    <body>
        <h2>📊 项目状态表盘</h2>
        <p>更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h3>📋 项目概览</h3>
        <ul>
            <li>总项目数: 8个</li>
            <li>已完成: 1个 (Stream运营系统)</li>
            <li>进行中: 5个</li>
            <li>未开始: 2个</li>
            <li>整体进度: 59%</li>
        </ul>
        
        <h3>📈 股票持仓</h3>
        <ul>
            <li>华联股份(000882): ¥1.66 (-11.37%) ⚠️接近止损</li>
            <li>中远海发(601866): ¥2.78 👀关注中</li>
        </ul>
        
        <h3>⚙️ 系统状态</h3>
        <ul>
            <li>OpenClaw: 🟢 运行中</li>
            <li>Ollama Cloud: 🟢 正常</li>
            <li>邮件系统: 🟢 正常</li>
            <li>监控系统: 🟡 优化中</li>
        </ul>
        
        <p><strong>附件包含:</strong></p>
        <ul>
            <li>project_dashboard.html - 交互式HTML表盘</li>
            <li>ascii_dashboard.txt - ASCII艺术表盘</li>
            <li>simple_dashboard.txt - 简化版表盘</li>
        </ul>
        
        <p>请在浏览器中打开HTML文件查看完整表盘效果。</p>
    </body>
    </html>
    """
    
    msg.attach(MimeText(body, 'html'))
    
    # 添加HTML附件
    html_path = "/root/.openclaw/workspace/ai_agent/results/project_dashboard.html"
    if os.path.exists(html_path):
        with open(html_path, 'rb') as f:
            attachment = MimeBase('application', 'octet-stream')
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename="project_dashboard.html"')
        msg.attach(attachment)
    
    # 添加ASCII表盘附件
    ascii_path = "/root/.openclaw/workspace/ai_agent/results/ascii_dashboard.txt"
    if os.path.exists(ascii_path):
        with open(ascii_path, 'rb') as f:
            attachment = MimeBase('application', 'octet-stream')
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename="ascii_dashboard.txt"')
        msg.attach(attachment)
    
    # 添加简化版表盘附件
    simple_path = "/root/.openclaw/workspace/ai_agent/results/simple_dashboard.txt"
    if os.path.exists(simple_path):
        with open(simple_path, 'rb') as f:
            attachment = MimeBase('application', 'octet-stream')
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename="simple_dashboard.txt"')
        msg.attach(attachment)
    
    try:
        # 发送邮件
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(email, auth_code)
        server.send_message(msg)
        server.quit()
        
        print("✅ 项目表盘邮件发送成功！")
        print(f"📧 收件人: {to_email}")
        print(f"📎 附件: 3个表盘文件")
        
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    send_dashboard_email()