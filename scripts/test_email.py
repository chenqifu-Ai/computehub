#!/usr/bin/env python3
"""测试邮件发送功能"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_email():
    """测试邮件发送"""
    try:
        # 邮件配置
        smtp_server = 'smtp.qq.com'
        smtp_port = 465
        email = '19525456@qq.com'
        auth_code = 'xunlwhjokescbgdd'
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = email
        msg['Subject'] = '🚀 股票预警系统测试邮件'
        
        # 邮件内容
        content = f"""
        <html>
        <body>
        <h2 style=\"color: #28a745;\">✅ 邮件系统测试成功</h2>
        <div style=\"background: #f8f9fa; padding: 20px; border-radius: 10px;\">
        <p>股票预警系统邮件功能测试成功！</p>
        <ul>
            <li>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
            <li>发件人: {email}</li>
            <li>收件人: {email}</li>
        </ul>
        </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(content, 'html'))
        
        # 发送邮件
        print("📧 正在发送测试邮件...")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(email, auth_code)
        server.send_message(msg)
        server.quit()
        
        print("✅ 邮件发送成功！")
        print(f"主题: 股票预警系统测试邮件")
        print(f"收件人: {email}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    test_email()