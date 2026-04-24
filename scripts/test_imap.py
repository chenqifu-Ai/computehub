import imaplib
import email
from email.header import decode_header
import sys
import os

# 从配置文件读取邮箱配置
config_path = os.path.expanduser('~/.openclaw/workspace/config/email.conf')
with open(config_path) as f:
    config = dict(line.strip().split('=') for line in f if '=' in line)

imap_server = config.get('IMAP_SERVER', 'imap.qq.com')
imap_port = int(config.get('IMAP_PORT', 993))
email_user = config.get('username', '')
email_pass = config.get('password', '')

def test_imap_connection():
    try:
        print(f"连接IMAP服务器: {imap_server}:{imap_port}")
        print(f"账号: {email_user}")
        
        # 连接IMAP服务器
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        print("✅ IMAP SSL连接成功")
        
        # 登录
        mail.login(email_user, email_pass)
        print("✅ IMAP登录成功")
        
        # 选择收件箱
        status, messages = mail.select("INBOX")
        print(f"✅ 选择收件箱: {status}, 邮件数量: {messages[0].decode()}")
        
        # 获取最新5封邮件
        status, messages = mail.search(None, 'ALL')
        if status == 'OK':
            email_ids = messages[0].split()
            print(f"找到 {len(email_ids)} 封邮件")
            
            # 获取最新5封邮件的主题
            for i, email_id in enumerate(email_ids[-5:]):
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    from_ = msg.get("From")
                    date = msg.get("Date")
                    print(f"{i+1}. 主题: {subject}")
                    print(f"   发件人: {from_}")
                    print(f"   日期: {date}")
                    print("   ---")
        
        mail.logout()
        print("✅ IMAP测试完成")
        return True
        
    except Exception as e:
        print(f"❌ IMAP测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    test_imap_connection()