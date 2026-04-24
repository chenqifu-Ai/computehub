# 邮件发送模块
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

def send_email_with_attachment(receiver_email, subject, body, attachments=None):
    """
    发送带附件的邮件
    
    Args:
        receiver_email: 接收邮箱
        subject: 邮件主题
        body: 邮件正文
        attachments: 附件文件路径列表
    """
    # 邮件配置（需要用户配置）
    sender_email = "your_email@qq.com"  # 需要配置发送邮箱
    sender_password = "your_app_password"  # QQ邮箱授权码
    smtp_server = "smtp.qq.com"
    smtp_port = 587
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    
    # 添加正文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 添加附件
    if attachments:
        for attachment_path in attachments:
            if os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
    
    try:
        # 发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        
        print(f"邮件已成功发送到 {receiver_email}")
        return True
        
    except Exception as e:
        print(f"发送邮件时出错: {e}")
        return False

def send_patent_data(receiver_email="19525456@qq.com"):
    """发送专利数据邮件"""
    attachments = []
    
    # 检查文件是否存在
    if os.path.exists("patents_data.json"):
        attachments.append("patents_data.json")
    if os.path.exists("patents_data.csv"):
        attachments.append("patents_data.csv")
    
    if not attachments:
        print("没有找到专利数据文件")
        return False
    
    subject = "中国知网专利数据采集结果"
    body = f"""您好！

这是从中国知网采集的专利数据，包含人工智能、机器学习、深度学习相关专利。

采集信息包括：
- 专利标题
- 专利号
- 申请人
- 发明人
- 摘要
- 申请日期

共采集到 {len(attachments)} 个数据文件。

请注意：数据仅供参考，请遵守相关法律法规。

Best regards,
专利数据采集系统
"""
    
    return send_email_with_attachment(receiver_email, subject, body, attachments)

if __name__ == "__main__":
    # 测试发送
    send_patent_data()