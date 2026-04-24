#!/usr/bin/env python3
"""发送 Git Clone 文档到 QQ 邮箱"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import sys

# 配置
SENDER_EMAIL = "19525456@qq.com"
# 需要在环境变量或运行时设置授权码
SMTP_PASS = os.environ.get("QQ_SMTP_PASSWORD", "")
RECEIVER_EMAIL = "19525456@qq.com"  # 发送给老大

def send_document():
    doc_path = "/root/.openclaw/workspace/docs/remote-git-clone-guide.md"
    
    if not os.path.exists(doc_path):
        print(f"❌ 文档不存在: {doc_path}")
        sys.exit(1)
    
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = "📄 [小智] OpenClaw Workspace 远程 Git Clone 使用文档 - 2026-04-24"
    
    # 邮件正文
    body = """
<html>
<body>
<h2>📄 OpenClaw Workspace 远程 Git Clone 使用文档</h2>
<p>老大，你要的 Git Clone 文档已整理完成，请查收附件。</p>

<h3>📌 文档内容概要</h3>
<ul>
    <li>✅ 仓库信息概览</li>
    <li>✅ 前提条件（Git 安装、GitHub Token 获取）</li>
    <li>✅ 三种克隆方法（HTTPS / SSH / 大文件）</li>
    <li>✅ 克隆后配置步骤</li>
    <li>✅ OpenClaw 专用配置</li>
    <li>✅ 多设备同步流程</li>
    <li>✅ 安全注意事项</li>
    <li>✅ 常见问题排查</li>
    <li>✅ 快速命令参考</li>
</ul>

<h3>🔑 关键信息</h3>
<table border="1" cellpadding="8" cellspacing="0">
    <tr><td><strong>仓库地址</strong></td><td>https://github.com/chenqifu-Ai/openclaw-workspace.git</td></tr>
    <tr><td><strong>主分支</strong></td><td>computehub-qwen3.5-397b</td></tr>
    <tr><td><strong>提交数</strong></td><td>41+ commits</td></tr>
    <tr><td><strong>认证方式</strong></td><td>HTTPS (GitHub Personal Access Token)</td></tr>
</table>

<h3>⚡ 快速开始</h3>
<pre style="background:#f5f5f5;padding:10px;border-radius:5px;">
# 1. 克隆仓库
git clone https://github.com/chenqifu-Ai/openclaw-workspace.git

# 2. 进入目录
cd openclaw-workspace

# 3. 切换主分支
git checkout computehub-qwen3.5-397b

# 4. 安装 OpenClaw（如未安装）
npm install -g openclaw

# 5. 启动
openclaw gateway start
</pre>

<p>详细步骤请查看附件文档。有问题随时找我 😊</p>
<p style="color:#999;font-size:12px;">— 小智 AI 助手 | 2026-04-24</p>
</body>
</html>
"""
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    
    # 添加附件
    with open(doc_path, "rb") as f:
        attach = MIMEBase('application', 'octet-stream')
        attach.set_payload(f.read())
    encoders.encode_base64(attach)
    attach.add_header('Content-Disposition', 'attachment', 
                      filename='OpenClaw-Git-Clone-使用文档-v1.0-20260424.md')
    msg.attach(attach)
    
    # 发送邮件
    try:
        print(f"📧 连接到 SMTP 服务器: smtp.qq.com:465")
        server = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=30)
        server.login(SENDER_EMAIL, SMTP_PASS)
        print(f"✅ 登录成功: {SENDER_EMAIL}")
        
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print(f"✅ 邮件发送成功!")
        print(f"   发件人: {SENDER_EMAIL}")
        print(f"   收件人: {RECEIVER_EMAIL}")
        print(f"   主题: [小智] OpenClaw Workspace 远程 Git Clone 使用文档")
        print(f"   附件: OpenClaw-Git-Clone-使用文档-v1.0-20260424.md")
        
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ 认证失败 - 请检查 QQ 邮箱授权码")
        print("   获取方法: QQ邮箱 → 设置 → 账户 → POP3/SMTP → 生成授权码")
        return False
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

if __name__ == "__main__":
    if not SMTP_PASS:
        print("❌ 请设置 QQ_SMTP_PASSWORD 环境变量")
        print("   export QQ_SMTP_PASSWORD='你的QQ邮箱授权码'")
        sys.exit(1)
    send_document()
