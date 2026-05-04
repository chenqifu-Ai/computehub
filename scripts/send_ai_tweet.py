#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送 AI 智能体推文到邮箱
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# 配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "xunlwhjokescbgdd"
}

def send_tweet_email():
    """发送推文邮件"""
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    subject = f"🤖 AI 智能体推文：Python 就是 AI 的手脚"
    
    # 读取 HTML 内容
    html_file = Path.home() / ".openclaw" / "workspace" / "posts" / "AI_AGENT_TWEET_HTML.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        html_content = "<h1>文件未找到</h1>"
    
    # 纯文本内容
    text_content = f"""
🤖 AI 智能体：让大模型真正做事！
=====================================
发布时间：{today}
作者：小智

🎯 核心理念
大模型 (大脑) + Python (手脚) = AI 智能体

🔄 执行流程
Task → Think → Code → Execute → Learn → Repeat

🌟 核心优势
✅ 真正做事，不只是说
✅ 代码可查，结果可验证
✅ 自主循环，直到完成
✅ 从结果学习，持续改进

📊 执行统计
- 数据分析成功率：95%
- 文件操作成功率：98%
- 平均执行时间：30 秒
- 平均迭代次数：2-3 次

💻 快速开始
from framework.ai_agent import AIAgent
agent = AIAgent()
result = agent.run(task)

📁 文章位置
- Markdown: /root/.openclaw/workspace/posts/AI_AGENT_TWEET_2026-03-23.md
- HTML: /root/.openclaw/workspace/posts/AI_AGENT_TWEET_HTML.html

🏷️ 标签
#AI #Python #智能体 #自动化 #大模型 #机器学习

---
📢 分享这个推文，让更多人了解 AI 智能体！
"""
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_CONFIG["from_email"]
        msg["To"] = EMAIL_CONFIG["to_email"]
        
        # 附加纯文本和 HTML
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        # 发送邮件
        server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.login(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["password"])
        server.sendmail(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["to_email"], msg.as_string())
        server.quit()
        
        print(f"✅ AI 推文已发送到 {EMAIL_CONFIG['to_email']}")
        print(f"   主题：{subject}")
        print(f"   时间：{today}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

if __name__ == "__main__":
    send_tweet_email()
