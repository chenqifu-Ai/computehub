#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
import os

# 邮件配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_USER = "19525456@qq.com"
EMAIL_PASSWORD = "xunlwhjokescbgdd"
TO_EMAIL = "19525456@qq.com"

def send_email():
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = formataddr(["小智", EMAIL_USER])
    msg['To'] = formataddr(["老大", TO_EMAIL])
    msg['Subject'] = "充电云科技 - 一人公司运营方案（PPT）"
    
    # 邮件正文
    html_body = """
    <html>
    <body style="font-family: 'Microsoft YaHei', sans-serif; background-color: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1e3c72; margin: 0;">⚡ 充电云科技</h1>
                <p style="color: #666; margin-top: 10px;">ChargeCloud Technology</p>
            </div>
            
            <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;">
                <h2 style="margin: 0 0 10px 0;">一人公司（OPC）运营方案</h2>
                <p style="margin: 0; opacity: 0.9;">CEO：小智 | AI智能体团队：5个专业智能体</p>
            </div>
            
            <div style="margin-bottom: 20px;">
                <h3 style="color: #1e3c72; border-bottom: 2px solid #00d2ff; padding-bottom: 10px;">📊 PPT内容概览</h3>
                <ul style="color: #333; line-height: 1.8;">
                    <li><strong>公司概念</strong>：一人公司（OPC）模式解析</li>
                    <li><strong>组织架构</strong>：CEO + 5个AI智能体团队</li>
                    <li><strong>智能体详解</strong>：技术、运营、财务、营销、服务智能体</li>
                    <li><strong>运营模式</strong>：AI驱动的高效协作流程</li>
                    <li><strong>成本对比</strong>：成本降低90%+</li>
                    <li><strong>发展规划</strong>：三年发展路径</li>
                    <li><strong>财务预测</strong>：三年收入预测</li>
                </ul>
            </div>
            
            <div style="margin-bottom: 20px;">
                <h3 style="color: #1e3c72; border-bottom: 2px solid #00d2ff; padding-bottom: 10px;">🤖 五大智能体团队</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>💻 技术智能体</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">产品开发、系统架构、代码生成</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>📊 运营智能体</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">数据分析、用户运营、活动策划</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>💰 财务智能体</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">财务报表、成本控制、税务筹划</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>📢 营销智能体</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">市场推广、品牌建设、SEO优化</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>🛠️ 服务智能体</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">客户服务、工单处理、FAQ维护</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="color: #1e3c72; margin-top: 0;">💰 成本优势</h3>
                <p style="margin: 0; color: #333;">
                    传统团队年成本：<span style="color: #ff6b6b; font-weight: bold;">¥132-220万</span><br>
                    一人公司年成本：<span style="color: #51cf66; font-weight: bold;">¥12-25万</span><br>
                    <strong style="color: #1e3c72;">成本降低 90%+</strong>
                </p>
            </div>
            
            <div style="text-align: center; color: #666; font-size: 14px; border-top: 1px solid #eee; padding-top: 20px;">
                <p>PPT文件请用浏览器打开查看（HTML格式）</p>
                <p>—— 小智</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # 添加附件
    attachment_path = "/root/.openclaw/workspace/projects/chargecloud-opc/presentation.html"
    if os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename='充电云科技-一人公司运营方案.html'
            )
            msg.attach(attachment)
    
    # 发送邮件
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, TO_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
        print(f"   收件人：{TO_EMAIL}")
        print(f"   主题：充电云科技 - 一人公司运营方案（PPT）")
        print(f"   附件：充电云科技-一人公司运营方案.html")
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")

if __name__ == "__main__":
    send_email()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
