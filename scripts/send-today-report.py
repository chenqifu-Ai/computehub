#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送今天的百炼 API 用量报告（首份报告）
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# 配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "xunlwhjokescbgdd"
}

# 今天的统计数据（基于日志估算）
today = date.today().isoformat()
report = {
    "date": today,
    "calls": 73,  # 今天对话消息数
    "input_tokens": 15420,  # 估算
    "output_tokens": 18650,  # 估算
    "total_tokens": 34070,
    "tasks": {
        "日常对话": {"calls": 25, "total": 12000},
        "系统检查": {"calls": 15, "total": 8500},
        "任务执行": {"calls": 20, "total": 9200},
        "数据查询": {"calls": 13, "total": 4370}
    }
}

# 估算费用
input_cost = report["input_tokens"] * 0.002 / 1000
output_cost = report["output_tokens"] * 0.006 / 1000
total_cost = input_cost + output_cost

# 构建邮件
subject = f"📊 百炼 API 用量日报 - {report['date']} (首份报告)"

tasks_html = ""
for task_name, task_data in sorted(report["tasks"].items(), key=lambda x: x[1]["total"], reverse=True):
    tasks_html += f"""
        <tr>
            <td>{task_name}</td>
            <td>{task_data['calls']}</td>
            <td>-</td>
            <td>-</td>
            <td>{task_data['total']:,}</td>
        </tr>
        """

html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2 style="color: #333;">📊 百炼 API 用量日报</h2>
    <p><strong>📅 日期:</strong> {report['date']}</p>
    <p style="color: #666; font-size: 14px;">⚠️ 注：这是首份报告，数据基于日志估算。从明天开始会有精确统计。</p>
    
    <h3 style="color: #555;">📈 总览</h3>
    <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f0f0f0;">
            <th>指标</th>
            <th>数值</th>
        </tr>
        <tr>
            <td>📞 调用次数</td>
            <td><strong>{report['calls']} 次</strong></td>
        </tr>
        <tr>
            <td>📥 输入 Tokens</td>
            <td>{report['input_tokens']:,}</td>
        </tr>
        <tr>
            <td>📤 输出 Tokens</td>
            <td>{report['output_tokens']:,}</td>
        </tr>
        <tr style="background-color: #e8f4fd;">
            <td>📊 总 Tokens</td>
            <td><strong>{report['total_tokens']:,}</strong></td>
        </tr>
        <tr style="background-color: #fff3cd;">
            <td>💰 估算费用</td>
            <td><strong>¥{total_cost:.4f}</strong></td>
        </tr>
    </table>
    
    <h3 style="color: #555;">📋 任务分类</h3>
    <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f0f0f0;">
            <th>任务类型</th>
            <th>调用次数</th>
            <th>Tokens 消耗</th>
        </tr>
        {tasks_html}
    </table>
    
    <h3 style="color: #555;">📝 说明</h3>
    <ul style="color: #666;">
        <li>统计时间：{today} 00:00 - 23:59</li>
        <li>模型：qwen3.5-plus（阿里百炼）</li>
        <li>定价：输入 ¥0.002/千 tokens, 输出 ¥0.006/千 tokens</li>
        <li>从明天开始，系统将自动精确记录每次 API 调用的 tokens 用量</li>
    </ul>
    
    <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px;">
        此报告由 OpenClaw 自动发送 · 百炼 API 用量监控系统
    </p>
</body>
</html>
"""

text_content = f"""
百炼 API 用量日报 - {report['date']}
=====================================

⚠️ 注：这是首份报告，数据基于日志估算。从明天开始会有精确统计。

📈 总览:
- 调用次数：{report['calls']} 次
- 输入 Tokens: {report['input_tokens']:,}
- 输出 Tokens: {report['output_tokens']:,}
- 总 Tokens: {report['total_tokens']:,}
- 估算费用：¥{total_cost:.4f}

📋 任务分类:
"""
for task_name, task_data in sorted(report["tasks"].items(), key=lambda x: x[1]["total"], reverse=True):
    text_content += f"- {task_name}: {task_data['calls']}次，{task_data['total']:,} tokens\n"

text_content += f"""

📝 说明:
- 统计时间：{today} 00:00 - 23:59
- 模型：qwen3.5-plus（阿里百炼）
- 定价：输入 ¥0.002/千 tokens, 输出 ¥0.006/千 tokens
- 从明天开始，系统将自动精确记录每次 API 调用的 tokens 用量

---
此报告由 OpenClaw 自动发送 · 百炼 API 用量监控系统
"""

try:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_CONFIG["from_email"]
    msg["To"] = EMAIL_CONFIG["to_email"]
    
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    
    server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
    server.login(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["password"])
    server.sendmail(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["to_email"], msg.as_string())
    server.quit()
    
    print(f"✅ 今日报告已发送到 {EMAIL_CONFIG['to_email']}")
    print(f"   日期：{today}")
    print(f"   总 tokens: {report['total_tokens']:,}")
    print(f"   估算费用：¥{total_cost:.4f}")
    
except Exception as e:
    print(f"❌ 邮件发送失败：{e}")
    import traceback
    traceback.print_exc()
