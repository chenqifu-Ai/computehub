#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送 ComputeHub 开发计划邮件给老大
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime
import configparser

# 读取邮箱配置
config = configparser.ConfigParser()
config.read('/root/.openclaw/workspace/config/email.conf', encoding='utf-8')

sender = config.get('email', 'username')
password = config.get('email', 'password')
smtp_server = config.get('email', 'smtp_server')
smtp_port = config.getint('email', 'smtp_port')
receiver = sender  # 发送给老大自己

# 邮件内容
subject = "🚀 ComputeHub 详细开发计划已提交 (8 周冲刺)"

# 获取当前分支和 commit 信息
import subprocess
result = subprocess.run(
    ['git', 'log', '--oneline', '-1'],
    cwd='/root/.openclaw/workspace',
    capture_output=True,
    text=True
)
commit_info = result.stdout.strip()

result = subprocess.run(
    ['git', 'branch', '--show-current'],
    cwd='/root/.openclaw/workspace',
    capture_output=True,
    text=True
)
branch_name = result.stdout.strip()

# 邮件正文
html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2563eb;">🚀 ComputeHub 详细开发计划</h2>
    
    <p><strong>老大</strong>，</p>
    
    <p>ComputeHub 项目的详细开发计划已完成并提交到 Git！</p>
    
    <h3 style="color: #1e40af;">📋 项目概况</h3>
    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>项目名称</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">ComputeHub - 分布式算力出海平台</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>开发周期</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">8-12 周</td>
        </tr>
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>目标版本</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">v1.0.0 → v2.0.0 (工业级系统)</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Git 分支</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;"><code>{branch_name}</code></td>
        </tr>
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>最新提交</strong></td>
            <td style="padding: 8px; border: 1px: #ddd;"><code>{commit_info}</code></td>
        </tr>
    </table>
    
    <h3 style="color: #1e40af;">📊 四大开发阶段</h3>
    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #2563eb; color: white;">
            <th style="padding: 10px; border: 1px solid #ddd;">阶段</th>
            <th style="padding: 10px; border: 1px solid #ddd;">时间</th>
            <th style="padding: 10px; border: 1px solid #ddd;">核心目标</th>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>第一阶段</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">2-3 周</td>
            <td style="padding: 8px; border: 1px solid #ddd;">基础架构建设 (API 网关、节点管理、数据库)</td>
        </tr>
        <tr style="background-color: #f9fafb;">
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>第二阶段</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">3-4 周</td>
            <td style="padding: 8px; border: 1px solid #ddd;">核心功能实现 (调度系统、物理监控、熔断机制)</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>第三阶段</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">2-3 周</td>
            <td style="padding: 8px; border: 1px solid #ddd;">区块链验证 (智能合约、双节点校验、计费)</td>
        </tr>
        <tr style="background-color: #f9fafb;">
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>第四阶段</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">2 周</td>
            <td style="padding: 8px; border: 1px solid #ddd;">性能优化扩展 (gRPC、可视化、多语言 SDK)</td>
        </tr>
    </table>
    
    <h3 style="color: #1e40af;">🎯 关键里程碑</h3>
    <ul style="list-style-type: none; padding-left: 0;">
        <li style="padding: 5px 0;">✅ <strong>M1 (第 2 周末)</strong>: 基础框架完成 (API 网关、节点注册、监控)</li>
        <li style="padding: 5px 0;">✅ <strong>M2 (第 4 周末)</strong>: 核心功能完成 (调度系统、状态机、防御机制)</li>
        <li style="padding: 5px 0;">✅ <strong>M3 (第 6 周末)</strong>: 区块链集成 + 物理验证层就绪</li>
        <li style="padding: 5px 0;">✅ <strong>M4 (第 8 周末)</strong>: 生产就绪 (可视化界面、SDK、部署)</li>
    </ul>
    
    <h3 style="color: #1e40af;">🔑 核心差异化特性</h3>
    <ol>
        <li><strong>物理心跳监控</strong> - 真实采集 GPU 温度、显存、网络延迟，防作弊</li>
        <li><strong>双节点冗余验证</strong> - 关键任务双节点执行，结果一致性校验</li>
        <li><strong>防御性调度</strong> - 区域失效率>30% 自动熔断，基于物理延迟匹配</li>
    </ol>
    
    <h3 style="color: #1e40af;">📁 相关文档</h3>
    <ul>
        <li><code>computehub_详细开发计划.md</code> - 8 周详细开发计划</li>
        <li><code>compute_overseas_server_stack.md</code> - 完整服务器软件栈方案</li>
    </ul>
    
    <h3 style="color: #1e40af;">🎯 成功标准</h3>
    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>系统可用性</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">≥99.9%</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>API 响应时间</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">&lt;100ms</td>
        </tr>
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>支持节点数</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">1000+</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>首月收入目标</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">$1000+</td>
        </tr>
    </table>
    
    <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px; margin: 20px 0;">
        <strong>💡 下一步行动:</strong><br>
        等待您的确认，即可开始第一阶段开发：
        <ul>
            <li>创建项目目录结构</li>
            <li>搭建 FastAPI 基础框架</li>
            <li>设计数据库模型</li>
            <li>配置 CI/CD 流水线</li>
        </ul>
    </div>
    
    <p style="margin-top: 20px;">
        祝好，<br>
        <strong>小智 🤖</strong><br>
        <span style="color: #6b7280; font-size: 0.9em;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
    </p>
</body>
</html>
"""

# 创建邮件
msg = MIMEMultipart('alternative')
msg['Subject'] = Header(subject, 'utf-8')
msg['From'] = sender
msg['To'] = receiver

# 添加 HTML 内容
html_part = MIMEText(html_content, 'html', 'utf-8')
msg.attach(html_part)

# 发送邮件
try:
    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    server.login(sender, password)
    server.sendmail(sender, [receiver], msg.as_string())
    server.quit()
    print(f"✅ 邮件发送成功！")
    print(f"   收件人：{receiver}")
    print(f"   主题：{subject}")
except Exception as e:
    print(f"❌ 邮件发送失败：{e}")
    raise
