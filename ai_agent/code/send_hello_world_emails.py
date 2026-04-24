#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送Hello World邮件到两个配置的邮箱
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

def send_email(config, recipient_email):
    """发送邮件"""
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = config['EMAIL']
        msg['To'] = recipient_email
        msg['Subject'] = Header('Hello World from 小智!', 'utf-8')
        
        # 邮件正文
        body = f"""
Hello World!

这是一封来自小智的测试邮件。
发送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}

祝您一切顺利！

-- 
小智 (AI助手)
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 连接SMTP服务器并发送邮件
        server = smtplib.SMTP_SSL(config['SMTP_SERVER'], int(config['SMTP_PORT']))
        server.login(config['EMAIL'], config['AUTH_CODE'])
        server.send_message(msg)
        server.quit()
        
        print(f"✅ 邮件成功发送到 {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ 发送邮件到 {recipient_email} 失败: {str(e)}")
        return False

def main():
    print("📧 开始发送Hello World邮件...")
    
    # QQ邮箱配置
    qq_config_file = "/root/.openclaw/workspace/config/email.conf"
    # 163邮箱配置  
    netease_config_file = "/root/.openclaw/workspace/config/163_email.conf"
    
    results = []
    
    # 给QQ邮箱发送邮件（使用163邮箱发送）
    if os.path.exists(netease_config_file):
        print("\n📤 使用163邮箱发送到QQ邮箱...")
        netease_config = load_email_config(netease_config_file)
        result = send_email(netease_config, "19525456@qq.com")
        results.append(("163 -> QQ", result))
    
    # 给163邮箱发送邮件（使用QQ邮箱发送）
    if os.path.exists(qq_config_file):
        print("\n📤 使用QQ邮箱发送到163邮箱...")
        qq_config = load_email_config(qq_config_file)
        result = send_email(qq_config, "chenqifu_fzu@163.com")
        results.append(("QQ -> 163", result))
    
    # 总结结果
    print("\n" + "="*50)
    print("📊 发送结果汇总:")
    success_count = 0
    for desc, result in results:
        status = "✅ 成功" if result else "❌ 失败"
        print(f"  {desc}: {status}")
        if result:
            success_count += 1
    
    print(f"\n总计: {success_count}/{len(results)} 封邮件发送成功")
    
    if success_count == len(results):
        print("🎉 所有Hello World邮件都已成功发送！")
    else:
        print("⚠️  部分邮件发送失败，请检查配置和网络连接。")

if __name__ == "__main__":
    main()