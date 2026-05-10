#!/usr/bin/env python3
"""发送 ComputeHub 架构文档到 QQ 邮箱"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import sys
import time

# 配置
CONFIG_PATH = "/root/.openclaw/workspace/config/email.conf"
docs_dir = "/root/.openclaw/workspace/projects/computehub"

# 读取邮箱配置
config = {}
with open(CONFIG_PATH) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip()

SMTP_SERVER = config.get('SMTP_SERVER', 'smtp.qq.com')
SMTP_PORT = int(config.get('SMTP_PORT', 465))
SENDER_EMAIL = config.get('EMAIL', '')
EMAIL_PASS = config.get('AUTH_CODE', '')
RECEIVER_EMAIL = "19525456@qq.com"  # 发送给老大

def send_emails():
    """发送多封邮件，每封带一个文档"""
    
    # 文档列表
    docs = [
        ("architecture-mindmap.md", "🧠 通用架构思维导图 - 三层核心架构设计"),
        ("b2b-deepseek-architecture.md", "🏢 B端企业私有化部署方案 - DeepSeek4集成架构"),
        ("b2b-architecture-final.md", "🎯 B端架构最终版 - 修正后的正确架构图"),
        ("deepseek-integration.md", "🔧 DeepSeek接入指南 - 详细配置和集成说明"),
        ("b2b-architecture-corrected.md", "📝 架构修正过程 - 完整的迭代记录"),
    ]
    
    success_count = 0
    
    for doc_file, doc_title in docs:
        doc_path = os.path.join(docs_dir, doc_file)
        
        if not os.path.exists(doc_path):
            print(f"❌ 文档不存在: {doc_path}")
            continue
        
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"[小智] ComputeHub架构文档: {doc_title} - {time.strftime('%Y-%m-%d')}"
        
        # 邮件正文
        body = f"""
<html>
<body>
<h2>📄 {doc_title}</h2>
<p>老大，ComputeHub 架构文档已整理完成，请查收附件。</p>

<h3>📌 文档概要</h3>
<p>文件大小: {os.path.getsize(doc_path) / 1024:.1f}K</p>
<p>创建时间: {time.strftime('%Y-%m-%d %H:%M')}</p>

<h3>📦 全部文档清单</h3>
<ol>
    <li>🧠《通用架构思维导图》- 三层核心架构设计</li>
    <li>🏢《B端企业私有化部署方案》- DeepSeek4集成架构</li>
    <li>🎯《B端架构最终版》- 修正后的正确架构图</li>
    <li>🔧《DeepSeek接入指南》- 详细配置和集成说明</li>
    <li>📝《架构修正过程》- 完整的迭代记录</li>
</ol>

<h3>🔑 架构核心</h3>
<p><strong>B端客户 → 私有DeepSeek4 → ComputeHub Gateway → 分布式算力 Worker</strong></p>

<p>详细文档请查看附件。有问题随时找我 😊</p>
<p style="color:#999;font-size:12px;">— 小智 AI 助手 | {time.strftime('%Y-%m-%d %H:%M')}</p>
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
                          filename=doc_file)
        msg.attach(attach)
        
        # 发送邮件
        try:
            print(f"📧 发送邮件: {doc_title}...")
            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
            else:
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
                server.starttls()
            
            server.login(SENDER_EMAIL, EMAIL_PASS)
            
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            
            print(f"   ✅ 发送成功!")
            print(f"   📎 {doc_file} ({os.path.getsize(doc_path)/1024:.1f}K)")
            
            server.quit()
            success_count += 1
            
            # 间隔 2 秒，避免被限流
            if success_count < len(docs):
                time.sleep(2)
                
        except Exception as e:
            print(f"   ❌ 发送失败: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 发送完成: {success_count}/{len(docs)} 封邮件")
    print(f"{'='*50}")
    
    return success_count == len(docs)

if __name__ == "__main__":
    if not EMAIL_PASS:
        print("❌ 请配置邮箱授权码")
        print(f"   配置文件: {CONFIG_PATH}")
        sys.exit(1)
    
    success = send_emails()
    sys.exit(0 if success else 1)
