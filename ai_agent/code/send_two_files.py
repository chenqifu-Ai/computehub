#!/usr/bin/env python3
"""Send contract files with safe filenames."""
import smtplib, os, sys
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from email.header import Header
from email.utils import formataddr

sys.path.insert(0, '/root/.openclaw/workspace')
from scripts.send_email import MAIL_ACCOUNTS

to_addr = "19525456@qq.com"
subject = Header("霞浦EOD项目授权书 + 数载合同修改版", "utf-8")

files = [
    ("/root/.openclaw/workspace/ai_agent/results/霞浦EOD项目_联合体授权书.docx", "EOD_LianhetiShouquan.docx"),
    ("/root/.openclaw/workspace/ai_agent/results/数载生态伙伴平台服务合同_中物版.docx", "ShuzaiHetong_Zhongwu_Version.docx"),
]

for fp, _ in files:
    if not os.path.exists(fp):
        print(f"文件不存在: {fp}")
        sys.exit(1)

for acct_idx, acct_name in [(0, "QQ"), (1, "163")]:
    acct = MAIL_ACCOUNTS[acct_idx]
    print(f"尝试 {acct_name} 邮箱...")
    try:
        msg = MIMEMultipart('mixed')
        msg['From'] = acct["addr"]
        msg['To'] = to_addr
        msg['Subject'] = subject

        html = '''<html><body style="font-family:sans-serif; padding:20px;">
<h2>霞浦EOD项目授权书 + 数载合同修改版</h2>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
<tr><th>附件名</th><th>说明</th></tr>
<tr><td>1. EOD_LianhetiShouquan.docx</td>
<td><b>霞浦EOD项目_联合体授权书</b><br>联合体内部授权</td></tr>
<tr><td>2. ShuzaiHetong_Zhongwu_Version.docx</td>
<td><b>数载生态伙伴平台服务合同_中物版</b><br>合同修改版</td></tr>
</table>
<hr>
<p style="color:#999;">由 小智 · 2026-05-21 08:10</p>
</body></html>'''
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        for fp, safe_name in files:
            with open(fp, 'rb') as f:
                data = f.read()
            part = MIMEBase('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document')
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=safe_name)
            part.add_header('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', name=safe_name)
            msg.attach(part)

        smtp = smtplib.SMTP_SSL(acct["smtp"], acct["port"], timeout=15)
        smtp.login(acct["addr"], acct["password"])
        smtp.sendmail(acct["addr"], [to_addr], msg.as_string())
        smtp.quit()
        print(f"✅ 已通过 {acct_name} 发送成功！")
        sys.exit(0)
    except Exception as e:
        print(f"  ❌ {acct_name} 失败: {e}，切换...")

print("❌ 所有邮箱发送失败")
sys.exit(1)
