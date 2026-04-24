import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os

# 读取163邮箱配置
config_path = os.path.expanduser('~/.openclaw/workspace/config/163_email.conf')
with open(config_path) as f:
    config = dict(line.strip().split('=') for line in f if '=' in line)

smtp_server = config.get('SMTP_SERVER', 'smtp.163.com')
smtp_port = int(config.get('SMTP_PORT', 465))
email_user = config.get('EMAIL', '')
email_pass = config.get('AUTH_CODE', '')

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
        print('用法: python send_email_163.py "主题" "内容文件" "收件人"')
        sys.exit(1)
    
    subject = sys.argv[1]
    body_file = sys.argv[2]
    to_email = sys.argv[3]
    
    with open(body_file, 'r', encoding='utf-8') as f:
        body = f.read()
    
    send_email(subject, body, to_email)