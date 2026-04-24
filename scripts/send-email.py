#!/usr/bin/env python3
"""
发送邮件脚本
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# 配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_ACCOUNT = "19525456@qq.com"
AUTH_CODE = "xunlwhjokescbgdd"

def send_email(to_addr, subject, content, html_content=None, attachment_path=None):
    """发送邮件"""
    # 创建邮件
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = to_addr
    msg['Subject'] = subject
    
    # 添加文本内容
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    
    # 添加HTML内容
    if html_content:
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    # 添加附件
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', 
                                 filename=os.path.basename(attachment_path))
            msg.attach(attachment)
    
    # 发送邮件
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ACCOUNT, AUTH_CODE)
            server.sendmail(EMAIL_ACCOUNT, to_addr, msg.as_string())
        print(f"邮件发送成功！收件人：{to_addr}")
        return True
    except Exception as e:
        print(f"邮件发送失败：{e}")
        return False

if __name__ == "__main__":
    # 收件人
    to_addr = "19525456@qq.com"
    
    # 主题
    subject = "【小智报告】企业战略执行与落地 - PPT演示文稿"
    
    # 文本内容
    content = """
老大，

小智已完成《企业战略执行与落地》PPT演示文稿的制作。

这份PPT包含以下内容：
1. 战略执行概述
2. 战略解码与分解
3. 组织保障
4. 执行机制建设
5. 过程管理
6. 评估与改进
7. 成功要素

请用浏览器打开附件查看精美的HTML演示文稿。

此致
小智
CEO战略顾问智能体
"""
    
    # HTML内容
    html_content = """
    <html>
    <body style="font-family: 'Microsoft YaHei', sans-serif; padding: 20px;">
        <h2 style="color: #e94560;">企业战略执行与落地 - PPT演示文稿</h2>
        <p>老大，</p>
        <p>小智已完成PPT演示文稿的制作，请查看附件。</p>
        <h3 style="color: #a2d2ff;">内容概要：</h3>
        <ul style="line-height: 2;">
            <li>一、战略执行概述</li>
            <li>二、战略解码与分解</li>
            <li>三、组织保障</li>
            <li>四、执行机制建设</li>
            <li>五、过程管理</li>
            <li>六、评估与改进</li>
            <li>七、成功要素</li>
        </ul>
        <p style="color: #888;">请用浏览器打开附件查看精美的HTML演示文稿。</p>
        <hr style="margin: 20px 0; border-color: #e94560;">
        <p style="color: #666;">
            小智<br>
            CEO战略顾问智能体<br>
            2026年3月21日
        </p>
    </body>
    </html>
    """
    
    # 附件路径
    attachment_path = "/root/.openclaw/workspace/output/strategy-execution-ppt.html"
    
    # 发送邮件
    send_email(to_addr, subject, content, html_content, attachment_path)