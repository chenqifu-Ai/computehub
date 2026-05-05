#!/usr/bin/env python3

from scripts.email_utils import load_config
"""
邮件命令检查脚本
读取指定邮箱中主题为"小智请执行"的邮件并执行命令
"""

import imaplib
import email
from email.header import decode_header
import json
import os
import subprocess
import sys

# 配置
IMAP_SERVER = "imap.qq.com"
IMAP_PORT = 993
EMAIL_ACCOUNT = "19525456@qq.com"
AUTH_CODE = "__USE_CONFIG__"
TARGET_SUBJECT = "小智请执行"

def decode_str(s):
    """解码字符串"""
    if s is None:
        return ""
    decoded = decode_header(s)
    result = []
    for content, charset in decoded:
        if isinstance(content, bytes):
            result.append(content.decode(charset or 'utf-8', errors='ignore'))
        else:
            result.append(content)
    return ''.join(result)

def connect_imap():
    """连接IMAP服务器"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_ACCOUNT, AUTH_CODE)
        mail.select('INBOX')
        return mail
    except Exception as e:
        print(f"连接失败: {e}")
        return None

def get_target_emails(mail):
    """获取目标邮件"""
    try:
        # 搜索所有未读邮件
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            return []
        
        email_ids = messages[0].split()
        target_emails = []
        
        for email_id in email_ids[-10:]:  # 只检查最近10封
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_str(msg.get('Subject', ''))
                    sender = decode_str(msg.get('From', ''))
                    
                    if TARGET_SUBJECT in subject:
                        # 获取邮件正文
                        body = get_email_body(msg)
                        target_emails.append({
                            'id': email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                            'subject': subject,
                            'sender': sender,
                            'body': body
                        })
        
        return target_emails
    except Exception as e:
        print(f"获取邮件失败: {e}")
        return []

def get_email_body(msg):
    """获取邮件正文"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass
    return body.strip()

def main():
    """主函数"""
    print("连接邮箱...")
    mail = connect_imap()
    if not mail:
        print("无法连接邮箱")
        sys.exit(1)
    
    print("检查邮件...")
    emails = get_target_emails(mail)
    
    if not emails:
        print(f"没有找到主题为'{TARGET_SUBJECT}'的新邮件")
        mail.close()
        mail.logout()
        return
    
    print(f"找到 {len(emails)} 封目标邮件")
    
    for e in emails:
        print(f"\n--- 邮件来自: {e['sender']} ---")
        print(f"主题: {e['subject']}")
        print(f"内容:\n{e['body']}")
        print("---")
    
    # 输出JSON供其他程序使用
    output = {
        'count': len(emails),
        'emails': emails
    }
    print(f"\n[JSON_OUTPUT]\n{json.dumps(output, ensure_ascii=False, indent=2)}")
    
    mail.close()
    mail.logout()

if __name__ == "__main__":
    main()
# 从统一配置加载
_cfg = load_config()
AUTH_CODE = _cfg["auth_code"]
