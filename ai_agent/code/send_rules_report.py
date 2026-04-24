#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送当前规则体系汇报到用户邮箱
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import time

def load_email_config(config_file):
    """加载邮箱配置文件"""
    config = {}
    with open(config_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    return config

def send_rules_report(config, recipient_email):
    """发送规则汇报邮件"""
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = config['EMAIL']
        msg['To'] = recipient_email
        msg['Subject'] = Header('📋 当前完整规则体系汇报 - 小智', 'utf-8')
        
        # 邮件正文
        body = f"""
📋 当前完整规则体系汇报

发送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}

🎯 核心执行原则
1. AI智能体SOP流程（必须严格遵守）
   - 思考 → 写代码 → 执行 → 学习 → 循环
   - 任何任务都必须生成完整Python脚本执行
   - 每步都要验证结果，不完成不罢休

2. 用户偏好优先级
   - 自主性: 有事自己解决，不要事事问
   - 执行力: 不要找借口，直接去做  
   - 效率: 批量操作一次性搞定，避免逐个API调用

🔒 安全边界
- 严禁扫描: 禁止扫描 192.168.2.7, 192.168.2.29 等设备
- 仅限目标: 只能扫描 192.168.2.134
- 外部操作: 发送邮件/公开内容前必须确认
- 数据隐私: 私有数据绝不外泄

📧 邮箱系统状态
- QQ邮箱: 19525456@qq.com ✅ 已验证正常
- 163邮箱: chenqifu_fzu@163.com ✅ 已验证正常  
- 邮件命令: 支持读取"小智请执行"邮件指令

🔄 版本控制规则
- 配置快照: 已建立完整版本控制系统
- 回退能力: 支持回退到任意时间点
- 最新快照: snapshot_2026-03-26T18-27-11-320545
- 跟踪文件: 5个核心配置文件

⚠️ 历史教训总结
1. SOP违规: 任何操作都必须走完整AI智能体流程
2. 批量效率: 批量操作必须用脚本一次性执行
3. 环境检查: 切换模型前先检查可用性
4. 意图确认: 不确定时要再次确认用户意图

📂 工作目录结构
- 代码: /root/.openclaw/workspace/ai_agent/code/
- 结果: /root/.openclaw/workspace/ai_agent/results/  
- 配置: /root/.openclaw/workspace/config/
- 记忆: /root/.openclaw/workspace/memory/

💡 当前待办事项
- 邮件命令检查功能 ✅ 已实现
- 小爱老师学习任务 🔄 执行中  
- 各专家轮换学习 🔄 执行中

---
总结: 系统已完全就绪，所有规则清晰明确，版本控制已建立，可以安全高效地执行任何任务！

-- 
小智 (AI助手)
来自 OpenClaw 系统
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 连接SMTP服务器并发送邮件
        server = smtplib.SMTP_SSL(config['SMTP_SERVER'], int(config['SMTP_PORT']))
        server.login(config['EMAIL'], config['AUTH_CODE'])
        server.send_message(msg)
        server.quit()
        
        print(f"✅ 规则汇报邮件成功发送到 {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ 发送规则汇报邮件到 {recipient_email} 失败: {str(e)}")
        return False

def main():
    print("📧 发送规则体系汇报到邮箱...")
    
    # QQ邮箱配置
    qq_config_file = "/root/.openclaw/workspace/config/email.conf"
    # 163邮箱配置  
    netease_config_file = "/root/.openclaw/workspace/config/163_email.conf"
    
    results = []
    
    # 发送到QQ邮箱（使用QQ邮箱自己发）
    if os.path.exists(qq_config_file):
        print("\n📤 发送规则汇报到QQ邮箱...")
        qq_config = load_email_config(qq_config_file)
        result = send_rules_report(qq_config, "19525456@qq.com")
        results.append(("QQ邮箱", result))
    
    # 发送到163邮箱（使用163邮箱自己发）
    if os.path.exists(netease_config_file):
        print("\n📤 发送规则汇报到163邮箱...")
        netease_config = load_email_config(netease_config_file)
        result = send_rules_report(netease_config, "chenqifu_fzu@163.com")
        results.append(("163邮箱", result))
    
    # 总结结果
    print("\n" + "="*50)
    print("📊 发送结果汇总:")
    success_count = 0
    for email_type, result in results:
        status = "✅ 成功" if result else "❌ 失败"
        print(f"  {email_type}: {status}")
        if result:
            success_count += 1
    
    print(f"\n总计: {success_count}/{len(results)} 封邮件发送成功")
    
    if success_count == len(results):
        print("🎉 规则汇报邮件已成功发送到所有邮箱！")
    else:
        print("⚠️  部分邮件发送失败，请检查配置和网络连接。")

if __name__ == "__main__":
    main()