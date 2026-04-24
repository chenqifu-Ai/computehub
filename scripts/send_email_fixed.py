import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os
import configparser

# 使用configparser读取配置文件
config_path = os.path.expanduser('~/.openclaw/workspace/config/email.conf')
config = configparser.ConfigParser()
config.read(config_path)

# 获取配置值
smtp_server = config.get('email', 'smtp_server', fallback='smtp.qq.com')
smtp_port = config.getint('email', 'smtp_port', fallback=465)
email_user = config.get('email', 'username', fallback='')
email_pass = config.get('email', 'password', fallback='')

def send_email(subject, body, to_email):
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        server.set_debuglevel(1)
        server.login(email_user, email_pass)
        server.sendmail(email_user, to_email, msg.as_string())
        server.quit()
        print('✅ 邮件已成功发送')
    except Exception as e:
        print(f'❌ 邮件发送失败: {str(e)}')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('用法: python send_email_fixed.py "主题" "内容文件" "收件人"')
        sys.exit(1)
    
    subject = sys.argv[1]
    body_file = sys.argv[2]
    to_email = sys.argv[3]
    
    with open(body_file, 'r', encoding='utf-8') as f:
        body = f.read()
    
    send_email(subject, body, to_email)