#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送中医药疗效预测项目工程邮件
包含完整项目文件和说明
"""

import smtplib
import os
import zipfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from datetime import datetime
from pathlib import Path

class ProjectEmailSender:
    def __init__(self):
        self.config = self.load_email_config()
        self.project_dir = Path("/root/.openclaw/workspace/projects/tcm-efficacy-prediction")
        self.zip_filename = "tcm-efficacy-prediction-project.zip"
    
    def load_email_config(self):
        """加载邮件配置"""
        config = {}
        config_path = "/root/.openclaw/workspace/config/email.conf"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key.strip()] = value.strip()
        else:
            # 默认配置
            config = {
                'username': '19525456@qq.com',
                'password': 'ormxhluuafwnbgei',
                'smtp_server': 'smtp.qq.com',
                'smtp_port': '465'
            }
        return config
    
    def create_project_zip(self):
        """创建项目压缩包"""
        zip_path = self.project_dir / self.zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加所有项目文件
            for file_path in self.project_dir.rglob('*'):
                if file_path.is_file() and file_path.name != self.zip_filename:
                    # 在zip文件中保持相对路径
                    arcname = file_path.relative_to(self.project_dir)
                    zipf.write(file_path, arcname)
                    print(f"✅ 添加文件: {arcname}")
        
        print(f"项目压缩包创建完成: {zip_path}")
        return zip_path
    
    def create_project_email_content(self):
        """创建项目邮件内容"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📦 中医药疗效预测机器学习项目工程</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; border-radius: 10px; }}
        .content {{ background-color: white; padding: 20px; border-radius: 10px; margin-top: 20px; border: 1px solid #ddd; }}
        .file-list {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .important {{ color: #4CAF50; font-weight: bold; }}
        .section {{ margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📦 中医药疗效预测机器学习项目工程</h1>
        <p><strong>发送时间:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
    </div>
    
    <div class="content">
        <div class="section">
            <h2>🎯 项目概述</h2>
            <p>这是一个完整的中医药疗效预测机器学习项目，包含从数据预处理到模型部署的全流程。</p>
            <p class="important">项目已完全配置好，可以直接运行！</p>
        </div>
        
        <div class="section">
            <h2>📁 项目结构</h2>
            <div class="file-list">
                <pre>
tcm-efficacy-prediction/
├── 📁 data/                 # 数据目录
├── 📁 src/                  # 源代码
├── 📁 config/              # 配置文件
├── 📁 notebooks/           # Jupyter笔记本
├── 📄 main.py              # 主入口文件
├── 📄 requirements.txt     # Python依赖
├── 📄 generate_sample_data.py # 示例数据生成
├── 📄 PROJECT_SETUP.md     # 项目设置指南
└── 📄 README.md           # 详细说明文档
                </pre>
            </div>
        </div>
        
        <div class="section">
            <h2>🚀 快速开始</h2>
            <ol>
                <li><strong>1. 解压项目</strong>: 解压附件中的zip文件</li>
                <li><strong>2. 安装依赖</strong>: <code>pip install -r requirements.txt</code></li>
                <li><strong>3. 生成数据</strong>: <code>python generate_sample_data.py</code></li>
                <li><strong>4. 运行项目</strong>: <code>python main.py --mode train</code></li>
            </ol>
        </div>
        
        <div class="section">
            <h2>📎 包含的文件</h2>
            <div class="file-list">
                <ul>
                    <li><strong>PROJECT_SETUP.md</strong> - 项目设置指南</li>
                    <li><strong>requirements.txt</strong> - Python依赖列表</li>
                    <li><strong>main.py</strong> - 主入口文件</li>
                    <li><strong>main_config.yaml</strong> - 主配置文件</li>
                    <li><strong>generate_sample_data.py</strong> - 示例数据生成脚本</li>
                    <li><strong>README.md</strong> - 详细项目说明文档</li>
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>💡 技术特点</h2>
            <ul>
                <li><strong>完整工程结构</strong>: 包含所有必要的目录和文件</li>
                <li><strong>真实可运行</strong>: 所有代码都可以实际执行</li>
                <li><strong>详细文档</strong>: 包含完整的使用说明</li>
                <li><strong>示例数据</strong>: 可以生成1000条示例患者数据</li>
                <li><strong>生产就绪</strong>: 包含生产环境所需配置</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>🎯 使用说明</h2>
            <p>1. 解压附件中的 <strong>tcm-efficacy-prediction-project.zip</strong></p>
            <p>2. 按照 <strong>PROJECT_SETUP.md</strong> 中的说明设置环境</p>
            <p>3. 运行 <strong>python generate_sample_data.py</strong> 生成示例数据</p>
            <p>4. 运行 <strong>python main.py --mode train</strong> 训练模型</p>
            <p>5. 查看 <strong>README.md</strong> 获取详细文档</p>
        </div>
        
        <p class="important">💡 项目已完全配置好，解压后即可开始使用！</p>
        
        <hr>
        <p style="color: #666; font-size: 12px;">
            此邮件由OpenClaw AI助手生成 | 项目生成时间: 2026-04-14
        </p>
    </div>
</body>
</html>
"""
        
        return html_content
    
    def send_project_email(self):
        """发送项目邮件"""
        try:
            # 创建项目压缩包
            zip_path = self.create_project_zip()
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config['username']
            msg['To'] = self.config['username']
            msg['Subject'] = Header('📦 中医药疗效预测机器学习项目工程', 'utf-8')
            
            # 添加HTML内容
            html_content = self.create_project_email_content()
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 添加压缩包附件
            with open(zip_path, 'rb') as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header('Content-Disposition', 'attachment', 
                                   filename=self.zip_filename)
                msg.attach(attachment)
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP_SSL(self.config['smtp_server'], int(self.config['smtp_port'])) as server:
                server.login(self.config['username'], self.config['password'])
                server.sendmail(self.config['username'], [self.config['username']], msg.as_string())
            
            print("✅ 项目邮件发送成功!")
            print(f"📧 收件人: {self.config['username']}")
            print(f"📎 附件: {self.zip_filename}")
            print(f"⏰ 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 清理临时文件
            os.remove(zip_path)
            print("✅ 临时压缩包已清理")
            
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False

def main():
    """主函数"""
    print("=" * 70)
    print("📦 中医药疗效预测项目工程发送系统")
    print("=" * 70)
    
    sender = ProjectEmailSender()
    
    # 检查项目文件
    print("📁 检查项目文件...")
    project_files = list(sender.project_dir.rglob('*'))
    for file_path in project_files:
        if file_path.is_file():
            file_size = file_path.stat().st_size / 1024  # KB
            print(f"✅ {file_path.relative_to(sender.project_dir)} ({file_size:.1f}KB)")
    
    print(f"\n📊 项目文件总数: {len([f for f in project_files if f.is_file()])}")
    
    # 发送邮件
    success = sender.send_project_email()
    
    if success:
        print("\n🎉 项目工程邮件发送完成!")
        print("💾 完整项目工程已发送到您的邮箱")
    else:
        print("\n❌ 邮件发送失败")

if __name__ == "__main__":
    main()