#!/usr/bin/env python3
"""
发送Token算力出海方案邮件预览
将HTML方案作为附件发送到指定邮箱
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from datetime import datetime

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'smtp_port': 465,
    'username': '19525456@qq.com',
    'password': 'ormxhluuafwnbgei',
    'from_email': '19525456@qq.com',
    'to_email': '19525456@qq.com',  # 发送给自己预览
    'cc_email': '3198880764@qq.com'  # 抄送备用邮箱
}

# 文件路径
HTML_FILES = [
    '/root/.openclaw/workspace/ai_agent/code/token_compute_visual.html',
    '/root/.openclaw/workspace/ai_agent/code/token_compute_overseas.html',
    '/root/.openclaw/workspace/ai_agent/code/token_compute_simple.html',
    '/root/.openclaw/workspace/ai_agent/code/token_compute_pdf_template.html',
    '/root/.openclaw/workspace/ai_agent/code/image_guidance.md'
]

def send_email_with_attachments():
    """发送带附件的邮件"""
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = EMAIL_CONFIG['from_email']
    msg['To'] = EMAIL_CONFIG['to_email']
    msg['Cc'] = EMAIL_CONFIG['cc_email']
    msg['Subject'] = f'Token算力出海方案预览 - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
    
    # 邮件正文
    email_body = """
    <h2>🌍 Token算力出海方案预览</h2>
    
    <p>您好！</p>
    
    <p>附件包含完整的Token算力出海方案HTML文档，请查收：</p>
    
    <ul>
        <li><strong>token_compute_visual.html</strong> - 图文并茂视觉版（推荐）</li>
        <li><strong>token_compute_overseas.html</strong> - 完整企业版</li>
        <li><strong>token_compute_simple.html</strong> - 简洁传播版</li>
        <li><strong>token_compute_pdf_template.html</strong> - PDF模板版</li>
        <li><strong>image_guidance.md</strong> - 图片替换指南</li>
    </ul>
    
    <h3>🎯 使用说明</h3>
    <ol>
        <li>下载附件到本地</li>
        <li>用浏览器打开HTML文件预览效果</li>
        <li>按图片指南替换真实图片</li>
        <li>根据需要选择合适版本使用</li>
    </ol>
    
    <h3>📊 方案特色</h3>
    <ul>
        <li>面向企业老板，简单易懂</li>
        <li>专业视觉设计，美观大方</li>
        <li>响应式布局，多设备适配</li>
        <li>包含市场数据和收益分析</li>
    </ul>
    
    <p>如有任何问题或需要修改，请随时联系。</p>
    
    <p>祝商祺！<br>小智AI助手</p>
    """
    
    msg.attach(MIMEText(email_body, 'html', 'utf-8'))
    
    # 添加附件
    for file_path in HTML_FILES:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)
                print(f"✅ 已添加附件: {filename}")
        else:
            print(f"⚠️  文件不存在: {file_path}")
    
    # 发送邮件
    try:
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
            
            # 收件人列表（主送+抄送）
            recipients = [EMAIL_CONFIG['to_email']]
            if EMAIL_CONFIG['cc_email']:
                recipients.append(EMAIL_CONFIG['cc_email'])
            
            server.sendmail(EMAIL_CONFIG['from_email'], recipients, msg.as_string())
            print("✅ 邮件发送成功！")
            print(f"📧 收件人: {EMAIL_CONFIG['to_email']}")
            print(f"📋 抄送: {EMAIL_CONFIG['cc_email']}")
            print(f"📎 附件数量: {len(HTML_FILES)}个文件")
            
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 开始发送Token算力出海方案预览邮件...")
    print("=" * 50)
    
    success = send_email_with_attachments()
    
    print("=" * 50)
    if success:
        print("🎉 邮件发送完成！请检查邮箱。")
        print("💡 提示: 附件HTML文件下载后直接用浏览器打开即可预览")
    else:
        print("❌ 邮件发送失败，请检查配置或网络连接")

    print("\n📋 文件位置说明:")
    for file_path in HTML_FILES:
        if os.path.exists(file_path):
            print(f"   📄 {os.path.basename(file_path)} - {file_path}")

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
