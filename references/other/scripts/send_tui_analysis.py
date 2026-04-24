#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI界面分析文档自动发送脚本
连续流技能创建示例
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import json
from datetime import datetime

class TUIEmailSender:
    """TUI分析文档邮件发送器"""
    
    def __init__(self):
        self.config_file = "/root/.openclaw/workspace/config/email.conf"
        self.tui_doc_file = "/root/.openclaw/workspace/TUI界面分析与连续流技能创建.md"
        self.recipient_email = "19525456@qq.com"
        self.email_config = self.load_email_config()
    
    def load_email_config(self):
        """加载邮箱配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"加载邮箱配置失败: {e}")
            return None
    
    def create_tui_analysis_doc(self):
        """创建TUI分析文档"""
        doc_content = """# TUI界面分析与连续流技能创建

## 1. TUI界面基本概念

### 1.1 定义与特点
- **TUI (Text-based User Interface)**: 基于文本的用户界面
- **核心特征**: 完全基于字符和文本，运行在终端环境中
- **优势**: 轻量级、高效、跨平台、资源占用少

### 1.2 TUI界面主要类型

#### 类型1: 命令行界面 (CLI)
- **特点**: 纯文本命令输入输出
- **示例**: Bash、PowerShell、Git命令行
- **优势**: 简洁、脚本化能力强

#### 类型2: 全屏文本界面
- **特点**: 占用整个终端屏幕
- **示例**: Vim、Nano、Htop
- **优势**: 信息展示全面

#### 类型3: 对话框界面
- **特点**: 弹出式对话框交互
- **示例**: Whiptail、Dialog
- **优势**: 结构化输入

#### 类型4: 进度条界面
- **特点**: 显示进度和状态
- **示例**: wget、curl进度条
- **优势**: 直观反馈

#### 类型5: 表格/列表界面
- **特点**: 数据表格化展示
- **示例**: 系统监控工具
- **优势**: 数据清晰

## 2. 连续流技能创建过程

### 2.1 技能创建流程
```
用户需求 → 需求分析 → 界面设计 → 代码实现 → 测试验证 → 文档生成 → 邮件发送
```

### 2.2 核心组件
- **输入处理器**: 解析用户需求
- **文档生成器**: 自动创建内容
- **邮件发送器**: 自动化发送
- **状态监控器**: 跟踪执行状态

## 3. 当前实现示例

### 3.1 自动化流程
本邮件就是通过连续流技能自动生成的：
1. 分析TUI界面类型需求
2. 生成详细文档内容
3. 配置邮件参数
4. 自动发送到指定邮箱

### 3.2 技术实现
- Python脚本自动化执行
- 配置文件管理
- 错误处理和日志记录
- 状态反馈机制

## 4. 应用价值

### 4.1 效率提升
- 减少人工交互步骤
- 自动化重复任务
- 提高执行准确性

### 4.2 技能扩展
- 可复用的技能模板
- 模块化设计
- 易于维护和扩展

---
*文档创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*发送者: 小智 - AI智能体*
*邮箱: {self.recipient_email}*
""".format(datetime=datetime, self=self)
        
        # 保存文档到文件
        with open(self.tui_doc_file, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        return doc_content
    
    def send_email(self, subject, content):
        """发送邮件"""
        if not self.email_config:
            print("邮箱配置加载失败，无法发送邮件")
            return False
        
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.email_config['email']
            msg['To'] = self.recipient_email
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 添加邮件正文
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 连接SMTP服务器
            with smtplib.SMTP_SSL(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.login(self.email_config['email'], self.email_config['password'])
                server.send_message(msg)
            
            print(f"邮件发送成功! 收件人: {self.recipient_email}")
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    def execute_workflow(self):
        """执行完整工作流"""
        print("开始执行TUI分析文档发送工作流...")
        
        # 步骤1: 创建文档
        print("1. 创建TUI分析文档...")
        doc_content = self.create_tui_analysis_doc()
        
        # 步骤2: 发送邮件
        print("2. 发送邮件...")
        subject = f"TUI界面分析与连续流技能创建 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        success = self.send_email(subject, doc_content)
        
        # 步骤3: 记录结果
        print("3. 记录执行结果...")
        result = {
            "timestamp": datetime.now().isoformat(),
            "recipient": self.recipient_email,
            "subject": subject,
            "status": "success" if success else "failed",
            "document_saved": os.path.exists(self.tui_doc_file)
        }
        
        # 保存执行记录
        log_file = "/root/.openclaw/workspace/memory/email_send_log.json"
        logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        logs.append(result)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        print(f"工作流执行完成! 状态: {result['status']}")
        return result

def main():
    """主函数"""
    sender = TUIEmailSender()
    result = sender.execute_workflow()
    
    # 输出执行摘要
    print("\n" + "="*50)
    print("执行摘要:")
    print(f"时间: {result['timestamp']}")
    print(f"收件人: {result['recipient']}")
    print(f"主题: {result['subject']}")
    print(f"状态: {result['status']}")
    print(f"文档保存: {result['document_saved']}")
    print("="*50)

if __name__ == "__main__":
    main()