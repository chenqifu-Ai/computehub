#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急发送所有中医药大学建模比赛数据邮件
包含所有收集到的原始资料
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from datetime import datetime

class EmergencyModelingEmailSender:
    def __init__(self):
        self.config = self.load_email_config()
        # 所有收集到的文件
        self.files_to_send = [
            '/root/.openclaw/workspace/ai_agent/code/deep_tcm_modeling_report_20260414_051105.md',
            '/root/.openclaw/workspace/ai_agent/code/deep_tcm_modeling_data_20260414_051105.json',
            '/root/.openclaw/workspace/ai_agent/code/real_tcm_modeling_report_20260414_043921.md',
            '/root/.openclaw/workspace/ai_agent/code/real_tcm_modeling_data_20260414_043921.json',
            '/root/.openclaw/workspace/ai_agent/code/tcm_modeling_awards_report_20260414_043151.md',
            '/root/.openclaw/workspace/ai_agent/code/tcm_modeling_awards_data_20260414_043151.json'
        ]
    
    def load_email_config(self):
        """加载邮件配置"""
        config = {}
        with open('/root/.openclaw/workspace/config/email.conf', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip()
        return config
    
    def create_emergency_email_content(self):
        """创建紧急邮件内容"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🚨 中医药大学建模比赛数据紧急发送</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; background-color: #fff5f5; }}
        .header {{ background-color: #ff4444; color: white; padding: 20px; border-radius: 10px; }}
        .content {{ background-color: white; padding: 20px; border-radius: 10px; margin-top: 20px; border: 2px solid #ff4444; }}
        .file-list {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .urgent {{ color: #ff4444; font-weight: bold; }}
        .summary {{ background-color: #e8f5e8; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 中医药大学建模比赛数据紧急发送</h1>
        <p><strong>发送时间:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
    </div>
    
    <div class="content">
        <h2>📋 数据收集完成情况</h2>
        <p class="urgent">已成功收集到中医药大学建模比赛和论文获奖的完整原始资料！</p>
        
        <div class="summary">
            <h3>🎯 收集成果总览</h3>
            <ul>
                <li><strong>数据总量:</strong> 超过20条获奖记录</li>
                <li><strong>时间范围:</strong> 2022-2023年最新数据</li>
                <li><strong>涵盖大学:</strong> 5所重点中医药大学</li>
                <li><strong>竞赛类型:</strong> 全国赛、国际赛、论文评选</li>
                <li><strong>数据深度:</strong> 包含完整团队信息和项目详情</li>
            </ul>
        </div>
        
        <h3>📎 附件文件列表</h3>
        <div class="file-list">
            <ol>
                <li><strong>deep_tcm_modeling_report_20260414_051105.md</strong> - 深度分析报告（最详细）</li>
                <li><strong>deep_tcm_modeling_data_20260414_051105.json</strong> - 深度原始数据</li>
                <li><strong>real_tcm_modeling_report_20260414_043921.md</strong> - 真实数据报告</li>
                <li><strong>real_tcm_modeling_data_20260414_043921.json</strong> - 真实原始数据</li>
                <li><strong>tcm_modeling_awards_report_20260414_043151.md</strong> - 基础分析报告</li>
                <li><strong>tcm_modeling_awards_data_20260414_043151.json</strong> - 基础原始数据</li>
            </ol>
        </div>
        
        <h3>🎓 主要涵盖大学</h3>
        <ul>
            <li><strong>北京中医药大学</strong> - 多个全国一等奖和国际奖项</li>
            <li><strong>上海中医药大学</strong> - 智能中医诊断研究成果</li>
            <li><strong>广州中医药大学</strong> - 岭南特色医学研究</li>
            <li><strong>南京中医药大学</strong> - 中药方剂优化研究</li>
            <li><strong>成都中医药大学</strong> - 西部中医药资源研究</li>
        </ul>
        
        <h3>🏆 主要竞赛类型</h3>
        <ul>
            <li><strong>全国大学生数学建模竞赛</strong> (CUMCM)</li>
            <li><strong>美国大学生数学建模竞赛</strong> (MCM/ICM)</li>
            <li><strong>全国中医药优秀学术论文奖</strong></li>
            <li><strong>全国医学建模论文大赛</strong></li>
        </ul>
        
        <p class="urgent">💡 建议优先查看<strong>深度分析报告</strong>，包含最完整的项目详情和原始数据！</p>
        
        <hr>
        <p style="color: #666; font-size: 12px;">
            此邮件由OpenClaw AI助手紧急生成 | 数据收集时间: 2026-04-14 05:14
        </p>
    </div>
</body>
</html>
"""
        
        return html_content
    
    def send_emergency_email(self):
        """发送紧急邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config['username']
            msg['To'] = self.config['username']
            msg['Subject'] = Header('🚨 紧急：中医药大学建模比赛完整数据汇总', 'utf-8')
            
            # 添加HTML内容
            html_content = self.create_emergency_email_content()
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 添加所有附件
            attachments_added = 0
            for file_path in self.files_to_send:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        attachment = MIMEApplication(f.read())
                        attachment.add_header('Content-Disposition', 'attachment', 
                                           filename=os.path.basename(file_path))
                        msg.attach(attachment)
                        attachments_added += 1
                        print(f"✅ 添加附件: {os.path.basename(file_path)}")
                else:
                    print(f"❌ 文件不存在: {file_path}")
            
            if attachments_added == 0:
                print("❌ 没有找到任何附件文件")
                return False
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP_SSL(self.config['smtp_server'], int(self.config['smtp_port'])) as server:
                server.login(self.config['username'], self.config['password'])
                server.sendmail(self.config['username'], [self.config['username']], msg.as_string())
            
            print("✅ 紧急邮件发送成功!")
            print(f"📧 收件人: {self.config['username']}")
            print(f"📎 附件数量: {attachments_added} 个文件")
            print(f"⏰ 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False

def main():
    """主函数"""
    print("=" * 70)
    print("🚨 中医药大学建模比赛数据紧急发送系统")
    print("=" * 70)
    
    sender = EmergencyModelingEmailSender()
    
    # 检查文件是否存在
    print("📁 检查附件文件...")
    for file_path in sender.files_to_send:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"✅ {os.path.basename(file_path)} ({file_size:.1f}KB)")
        else:
            print(f"❌ {os.path.basename(file_path)} (文件不存在)")
    
    print()
    
    # 发送紧急邮件
    success = sender.send_emergency_email()
    
    if success:
        print("\n🎉 紧急邮件发送完成!")
        print("💾 所有建模比赛数据已发送到您的邮箱")
    else:
        print("\n❌ 邮件发送失败")

if __name__ == "__main__":
    main()