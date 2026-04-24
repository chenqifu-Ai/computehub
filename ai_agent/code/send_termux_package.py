#!/usr/bin/env python3
"""
发送 Termux 打包文件到邮箱
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime

def send_email_with_attachment():
    """发送带附件的邮件"""
    
    # 邮件配置
    sender_email = "19525456@qq.com"
    receiver_email = "19525456@qq.com"
    password = "xunlwhjokescbgdd"
    
    # 邮件内容
    subject = "Termux OpenClaw 安装包"
    body = """
你好！

这是你要的 Termux OpenClaw 安装包。

包含内容：
- 安装脚本 (install.sh)
- 配置文件
- 安装指南

由于 Android 安全限制，无法直接生成 APK 文件。
请查看 INSTALL_GUIDE.md 了解安装方法。

安装步骤：
1. 安装 Termux (F-Droid)
2. 解压此包
3. 运行 install.sh

如有问题随时联系！

小智
"""
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # 添加附件
    package_file = "/root/.openclaw/workspace/openclaw-termux-package.zip"
    
    if os.path.exists(package_file):
        attachment = open(package_file, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=openclaw-termux-package.zip")
        msg.attach(part)
        attachment.close()
    
    # 发送邮件
    try:
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        
        print("✅ 邮件发送成功！")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    """主函数"""
    
    print("📧 开始发送 Termux 安装包邮件...")
    
    success = send_email_with_attachment()
    
    if success:
        print("✅ Termux 安装包已发送到邮箱")
        print("📬 收件人: 19525456@qq.com")
        print("📎 附件: openclaw-termux-package.zip")
    else:
        print("❌ 发送失败，请检查网络或邮箱配置")

if __name__ == "__main__":
    main()