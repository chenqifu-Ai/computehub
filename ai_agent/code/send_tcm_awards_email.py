#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送中医药大学获奖分析报告邮件
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from datetime import datetime

class TCMAwardsEmailSender:
    def __init__(self):
        self.config = self.load_email_config()
        self.report_file = '/root/.openclaw/workspace/ai_agent/code/tcm_awards_pure_analysis_20260414_041929.md'
        self.data_file = '/root/.openclaw/workspace/ai_agent/code/tcm_awards_complete_data_20260414_041229.json'
    
    def load_email_config(self):
        """加载邮件配置"""
        config = {}
        with open('/root/.openclaw/workspace/config/email.conf', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip()
        return config
    
    def read_file_content(self, file_path):
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取文件 {file_path} 失败: {e}")
            return None
    
    def create_email_content(self):
        """创建邮件内容"""
        # 读取报告内容
        report_content = self.read_file_content(self.report_file)
        if not report_content:
            return None
        
        # 创建HTML格式的邮件内容
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>中医药大学获奖分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
        h2 {{ color: #34495e; }}
        h3 {{ color: #7f8c8d; }}
        .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .highlight {{ color: #e74c3c; font-weight: bold; }}
        .stat {{ background-color: #ecf0f1; padding: 10px; margin: 5px 0; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>📊 中医药大学获奖分析报告</h1>
    
    <div class="summary">
        <h2>📋 报告概要</h2>
        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        <p><strong>数据范围:</strong> 2009-2021年</p>
        <p><strong>涵盖院校:</strong> 5所重点中医药大学</p>
        <p><strong>总获奖数:</strong> <span class="highlight">19项</span>国家级和部省级奖项</p>
    </div>
    
    <h2>🏆 核心发现</h2>
    
    <div class="stat">
        <h3>🎓 大学排名</h3>
        <ol>
            <li><strong>北京中医药大学</strong>: 6项 (31.6%)</li>
            <li><strong>上海中医药大学</strong>: 5项 (26.3%)</li>
            <li><strong>广州中医药大学</strong>: 4项 (21.1%)</li>
            <li><strong>南京中医药大学</strong>: 3项 (15.8%)</li>
            <li><strong>成都中医药大学</strong>: 1项 (5.3%)</li>
        </ol>
    </div>
    
    <div class="stat">
        <h3>📊 奖项分布</h3>
        <ul>
            <li><strong>国家级教学成果奖</strong>: 10项 (52.6%)</li>
            <li><strong>国家科技进步奖</strong>: 4项 (21.1%)</li>
            <li>其他奖项: 5项 (26.3%)</li>
        </ul>
    </div>
    
    <div class="stat">
        <h3>🌟 卓越成就</h3>
        <ul>
            <li><strong>特等奖项目</strong>: 3项</li>
            <li><strong>高峰年份</strong>: 2018年 (6项获奖)</li>
            <li><strong>研究领域</strong>: 17个不同方向</li>
        </ul>
    </div>
    
    <h2>📎 附件说明</h2>
    <p>本邮件包含以下附件：</p>
    <ol>
        <li><strong>tcm_awards_pure_analysis_20260414_041929.md</strong> - 完整分析报告 (Markdown格式)</li>
        <li><strong>tcm_awards_complete_data_20260414_041229.json</strong> - 原始数据文件 (JSON格式)</li>
    </ol>
    
    <p>详细分析请查看附件中的完整报告。</p>
    
    <hr>
    <p style="color: #7f8c8d; font-size: 12px;">
        此邮件由OpenClaw AI助手自动生成 | 数据收集时间: 2026-04-14
    </p>
</body>
</html>
"""
        
        return html_content
    
    def send_email(self):
        """发送邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config['username']
            msg['To'] = self.config['username']  # 发送给自己
            msg['Subject'] = Header('中医药大学获奖分析报告 - 完整版', 'utf-8')
            
            # 添加HTML内容
            html_content = self.create_email_content()
            if html_content:
                msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 添加报告附件
            if os.path.exists(self.report_file):
                with open(self.report_file, 'rb') as f:
                    report_attachment = MIMEApplication(f.read())
                    report_attachment.add_header('Content-Disposition', 'attachment', 
                                               filename=os.path.basename(self.report_file))
                    msg.attach(report_attachment)
            
            # 添加数据附件
            if os.path.exists(self.data_file):
                with open(self.data_file, 'rb') as f:
                    data_attachment = MIMEApplication(f.read())
                    data_attachment.add_header('Content-Disposition', 'attachment',
                                             filename=os.path.basename(self.data_file))
                    msg.attach(data_attachment)
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP_SSL(self.config['smtp_server'], int(self.config['smtp_port'])) as server:
                server.login(self.config['username'], self.config['password'])
                server.sendmail(self.config['username'], [self.config['username']], msg.as_string())
            
            print("✅ 邮件发送成功!")
            print(f"📧 收件人: {self.config['username']}")
            print(f"📎 附件: {os.path.basename(self.report_file)}")
            print(f"📎 附件: {os.path.basename(self.data_file)}")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False

def main():
    """主函数"""
    print("=" * 60)
    print("中医药大学获奖分析报告邮件发送系统")
    print("=" * 60)
    
    sender = TCMAwardsEmailSender()
    
    # 检查文件是否存在
    if not os.path.exists(sender.report_file):
        print(f"❌ 报告文件不存在: {sender.report_file}")
        return
    
    if not os.path.exists(sender.data_file):
        print(f"❌ 数据文件不存在: {sender.data_file}")
        return
    
    print(f"📄 报告文件: {sender.report_file}")
    print(f"📊 数据文件: {sender.data_file}")
    print(f"📧 发件邮箱: {sender.config['username']}")
    print()
    
    # 发送邮件
    success = sender.send_email()
    
    if success:
        print("\n🎉 邮件发送完成!")
    else:
        print("\n❌ 邮件发送失败")

if __name__ == "__main__":
    main()