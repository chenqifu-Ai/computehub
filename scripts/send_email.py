#!/usr/bin/env python3
"""
STD-003: 邮件发送标准脚本
Usage:
  python3 scripts/send_email.py <to> <subject> <content_file>
  python3 scripts/send_email.py 19525456@qq.com "报告标题" /tmp/report.md
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import sys
import os

# 邮件账户配置（来源: config/email.conf）
# 主授权码: bzgwylbbrocdbiie (2026-05-21 更新)
# 备用授权码: AWZBPidhza74EbV8 (163邮箱)
MAIL_ACCOUNTS = [
    {
        "name": "QQ邮箱",
        "addr": "19525456@qq.com",
        "smtp": "smtp.qq.com",
        "port": 465,
        "password": "bzgwylbbrocdbiie",
    },
    {
        "name": "163邮箱",
        "addr": "chenqifu_fzu@163.com",
        "smtp": "smtp.163.com",
        "port": 465,
        "password": "AWZBPidhza74EbV8",  # 备用（原主授权码 ormxhluuafwnbgei 已退役）
    },
]


def send_email(to_addr, subject, content_path, account_index=0):
    """
    发送邮件
    参数:
        to_addr: 收件人
        subject: 主题
        content_path: 内容文件路径
        account_index: 邮箱索引 (0=QQ, 1=163)
    返回: True/False
    """
    acct = MAIL_ACCOUNTS[account_index]
    
    # 读取内容
    with open(content_path, 'rb') as f:
        content = f.read()
    
    # 判断文件类型
    ext = os.path.splitext(content_path)[1].lower()
    
    msg = MIMEMultipart('mixed')
    msg['From'] = acct["addr"]
    msg['To'] = to_addr
    msg['Subject'] = subject
    
    # MIME类型映射（避免附件显示为 .bin）
    MIME_MAP = {
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pdf':  'application/pdf',
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png':  'image/png',
        '.gif':  'image/gif',
        '.zip':  'application/zip',
        '.tar':  'application/x-tar',
        '.gz':   'application/gzip',
    }
    
    if ext in ('.md', '.txt', '.log'):
        # 文本 → HTML
        html_body = ('<html><head><meta charset="utf-8"></head><body>'
                     '<pre style="font-family:monospace;font-size:14px;white-space:pre-wrap">'
                     + content.decode('utf-8') +
                     '</pre></body></html>')
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    elif ext in MIME_MAP:
        # 附件（用正确MIME类型，避免显示为 .bin）
        mime_type = MIME_MAP[ext]
        maintype, subtype = mime_type.split('/', 1)
        part = MIMEBase(maintype, subtype)
        part.set_payload(content)
        encoders.encode_base64(part)
        fname = os.path.basename(content_path)
        # 用 RFC 2231 编码中文文件名，避免邮件客户端显示为 .bin
        from email.utils import encode_rfc2231
        encoded_name = encode_rfc2231(fname, 'utf-8')
        part.add_header('Content-Disposition', 'attachment', filename=encoded_name)
        # 同时设置正确MIME类型（部分客户端用）
        part.set_type(mime_type)
        msg.attach(part)
    else:
        # 默认作为 html
        html_body = '<html><body><pre>' + content.decode('utf-8', errors='replace') + '</pre></body></html>'
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # 发送
    try:
        smtp = smtplib.SMTP_SSL(acct["smtp"], acct["port"], timeout=10)
        smtp.login(acct["addr"], acct["password"])
        smtp.sendmail(acct["addr"], [to_addr], msg.as_string())
        smtp.quit()
        print(f"✅ 已通过 {acct['name']} 发送到 {to_addr}")
        return True
    except smtplib.SMTPServerDisconnected:
        print(f"❌ {acct['name']} 连接断开（可能被临时封锁）")
        return False
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ {acct['name']} 认证失败: {e}")
        return False
    except Exception as e:
        print(f"❌ {acct['name']} 发送失败: {e}")
        return False


def send_auto(to_addr, subject, content_path):
    """
    自动选择邮箱发送（QQ优先 → 163备选）
    """
    print(f"📧 发送邮件: {subject}")
    print(f"   收件人: {to_addr}")
    print(f"   附件:   {content_path}")
    print()
    
    # 优先 QQ 邮箱
    print("→ 尝试 QQ 邮箱...")
    if send_email(to_addr, subject, content_path, account_index=0):
        return True
    
    # QQ 失败，切 163
    print("→ QQ 失败，切换 163 邮箱...")
    if send_email(to_addr, subject, content_path, account_index=1):
        return True
    
    print("❌ 所有邮箱发送失败")
    return False


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python3 scripts/send_email.py <to> <subject> <content_file>")
        print()
        print("Examples:")
        print("  python3 scripts/send_email.py 19525456@qq.com '日报' /tmp/report.md")
        print("  python3 scripts/send_email.py 19525456@qq.com '报告' report.pdf")
        sys.exit(1)
    
    ok = send_auto(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if ok else 1)
