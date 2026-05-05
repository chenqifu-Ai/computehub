#!/usr/bin/env python3
"""发送情况说明模板到邮箱"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/scripts')
from mail_util import send_email

with open('/root/.openclaw/workspace/ai_agent/results/情况说明模板-永丰中物肉食品有限公司.txt', 'r') as f:
    body = f.read()

html_body = "<h2>情况说明模板 — 永丰中物肉食品有限公司破产清算</h2>"
html_body += "<p>生成日期：2026-05-05</p>"
html_body += "<p>⚠️ 仅供参考，建议律师审核后提交</p>"
html_body += "<hr>"
html_body += "<pre>" + body + "</pre>"
html_body += "<hr>"
html_body += "<p><small>此邮件由小智自动生成。</small></p>"

send_email(
    "情况说明模板 — 永丰中物肉食品有限公司破产清算",
    body,
    html_body=html_body
)

print("✅ 邮件发送完成 → 19525456@qq.com")
