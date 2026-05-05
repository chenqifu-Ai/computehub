#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送证券公司成立通知邮件 - 使用现有配置
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

class CompanyAnnouncementEmail:
    def __init__(self):
        self.config = {
            "smtp_server": "smtp.qq.com",
            "smtp_port": 465,
            "email": "19525456@qq.com",
            "auth_code": "xunlwhjokescbgdd"
        }
        
    def create_email_content(self):
        """创建邮件内容"""
        subject = "🏦 证券公司正式成立通知"
        
        body = f"""尊敬的老大（投资者）：

🏦 证券公司于2026年3月27日正式成立！

【成立时间】2026年3月27日 07:00
【公司使命】努力赚钱
【CEO】小智

【创始七杰团队】
💰 金算子（金融顾问） - 交易策略专家
📊 财神爷（财务专家） - 财务管理专家  
⚖️ 法海（法律顾问） - 风险控制专家
💻 码神（网络专家） - 技术开发专家
🚀 销冠王（营销专家） - 业务拓展专家
🎯 智多星（CEO顾问） - 战略规划专家
👥 人精（HR专家） - 人事管理专家

【当前运营状态】
✅ 公司架构已完善
✅ 专家任务已分配
✅ 监督机制已建立
✅ 连续流技能已应用
✅ 邮件系统已验证

【赚钱目标】
• 月利润目标：¥100,000
• 上市目标：2027年3月27日
• 公司格言：不赚钱，毋宁死

感谢您的投资信任！证券公司将全力以赴创造价值！

此致
敬礼！

小智
证券公司CEO
{datetime.now().strftime('%Y年%m月%d日 %H:%M')}"""
        
        return subject, body
    
    def send_email(self, subject, body):
        """发送邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config['email']
            msg['To'] = self.config['email']  # 发送给自己
            msg['Subject'] = subject
            
            # 添加邮件正文
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP_SSL(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.login(self.config['email'], self.config['auth_code'])
                server.send_message(msg)
                
            return True, "邮件发送成功"
            
        except Exception as e:
            return False, f"邮件发送失败: {str(e)}"
    
    def run(self):
        """执行发送流程"""
        print("📧 开始发送证券公司成立通知邮件...")
        
        # 创建邮件内容
        subject, body = self.create_email_content()
        print("✅ 邮件内容创建完成")
        
        # 发送邮件
        success, message = self.send_email(subject, body)
        
        if success:
            print("✅ 邮件发送成功！")
            print(f"📨 收件人: {self.config['email']}")
            print(f"📋 主题: {subject}")
        else:
            print("❌ 邮件发送失败")
            print(f"💡 错误信息: {message}")
        
        return success, message

if __name__ == "__main__":
    email_sender = CompanyAnnouncementEmail()
    success, message = email_sender.run()
    
    print("\n" + "="*60)
    if success:
        print("🎉 证券公司成立通知邮件已发送！")
    else:
        print("⚠️ 邮件发送遇到问题，需要检查配置")

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
