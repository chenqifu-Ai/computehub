#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送 ComputeHub 架构文档到邮箱"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 邮件配置
smtp_server = "smtp.qq.com"
smtp_port = 465
sender_email = "19525456@qq.com"
auth_code = "bzgwylbbrocdbiie"
receiver_email = "19525456@qq.com"

# 读取架构文档
with open("/root/.openclaw/workspace/ai_agent/code/computehub/ARCHITECTURE.md", "r", encoding="utf-8") as f:
    arch_content = f.read()

# 创建邮件
msg = MIMEMultipart()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = "ComputeHub 工程架构文档 (Sprint 4)"

body = """老大您好！

ComputeHub 工程架构文档已附上。

当前完成状态: Sprint 4 (Web Dashboard)
- Go代码: ~7,500行  |  测试: 56+  |  包: 9  |  API端点: 40+
- 全量测试: 9/9 包全部通过 ✅

架构概要:
┌── 入口层: CLI + TUI (2入口)
├── 网关层: Gateway (40+ REST端点)
├── 引擎层: 内核→纯化→执行→基因 (Sprint1)
├── 分布式: 节点管理→智能调度 (Sprint2)
├── 结算层: Token→4合约→5种计费 (Sprint3)
└── 界面层: HTMX Web仪表板 (Sprint4)

详情见附件 ARCHITECTURE.md（含完整 mermaid 架构图）。

小智
"""

msg.attach(MIMEText(body, 'plain', 'utf-8'))

# 添加附件
attachment = MIMEText(arch_content, 'plain', 'utf-8')
attachment.add_header('Content-Disposition', 'attachment', filename='ComputeHub_ARCHITECTURE.md')
msg.attach(attachment)

try:
    server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
    server.login(sender_email, auth_code)
    server.sendmail(sender_email, [receiver_email], msg.as_string())
    server.quit()
    print("✅ 架构文档已发送到 19525456@qq.com")
except Exception as e:
    print(f"❌ 发送失败: {e}")
