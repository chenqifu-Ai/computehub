#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送邮件脚本 - 将专利数据发送到指定邮箱
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

def send_email_with_attachments(
    to_email="19525456@qq.com",
    subject="中国知网专利数据",
    body="附件是中国知网专利数据爬取结果",
    attachment_files=None
):
    """发送带附件的邮件"""
    
    # 邮件服务器配置（需要用户提供SMTP信息）
    smtp_server = "smtp.qq.com"  # QQ邮箱SMTP服务器
    smtp_port = 587
    from_email = "your_email@qq.com"  # 需要替换为实际发件邮箱
    password = "your_password"  # 需要替换为实际密码或授权码
    
    # 如果没有提供附件文件，使用默认文件
    if attachment_files is None:
        attachment_files = []
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # 添加正文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 添加附件
    for file_path in attachment_files:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            msg.attach(part)
    
    try:
        # 连接服务器并发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # 启用TLS加密
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        
        print(f"邮件已成功发送到 {to_email}")
        print(f"附件: {', '.join([os.path.basename(f) for f in attachment_files])}")
        return True
        
    except Exception as e:
        print(f"发送邮件失败: {e}")
        print("请检查SMTP服务器配置和邮箱密码/授权码")
        return False

def main():
    """主函数"""
    print("邮件发送脚本")
    print("=" * 40)
    
    # 查找最新的专利数据文件
    code_dir = "/root/.openclaw/workspace/ai_agent/code"
    files = []
    
    if os.path.exists(code_dir):
        for file in os.listdir(code_dir):
            if file.startswith("cnki_patents_") and (file.endswith(".json") or file.endswith(".csv")):
                files.append(os.path.join(code_dir, file))
    
    if not files:
        print("未找到专利数据文件")
        return
    
    # 按修改时间排序，取最新的文件
    files.sort(key=os.path.getmtime, reverse=True)
    latest_files = files[:2]  # 取最新的两个文件（JSON和CSV）
    
    print(f"找到数据文件: {[os.path.basename(f) for f in latest_files]}")
    
    # 发送邮件（需要用户配置SMTP信息）
    print("\n注意: 需要配置SMTP信息才能发送邮件")
    print("请提供以下信息:")
    print("1. 发件邮箱地址")
    print("2. 邮箱密码或授权码")
    print("3. SMTP服务器地址和端口")
    print("\n当前脚本已准备好，但需要用户配置后才能实际发送")
    
    # 显示邮件内容预览
    print("\n邮件内容预览:")
    print(f"收件人: 19525456@qq.com")
    print(f"主题: 中国知网专利数据爬取结果")
    print(f"正文: 附件是中国知网专利数据爬取结果，包含专利标题、专利号、申请人、发明人、摘要、申请日期等信息。")
    print(f"附件: {', '.join([os.path.basename(f) for f in latest_files])}")

if __name__ == "__main__":
    main()