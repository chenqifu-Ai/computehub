#!/usr/bin/env python3
"""
测试邮件发送脚本 - 用于定时任务
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os
import json

def read_email_config():
    """读取邮箱配置"""
    # QQ邮箱配置
    qq_config = {
        'email': '19525456@qq.com',
        'password': 'xunlwhjokescbgdd',
        'smtp_server': 'smtp.qq.com',
        'smtp_port': 465
    }
    
    # 163邮箱配置
    mail163_config = {
        'email': 'chenqifu_fzu@163.com',
        'password': 'AWZBPidhza74EbV8',
        'smtp_server': 'smtp.163.com',
        'smtp_port': 465
    }
    
    return qq_config, mail163_config

def send_email(config, to_email, subject, content):
    """发送邮件"""
    try:
        # 创建邮件内容
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = Header(config['email'], 'utf-8')
        msg['To'] = Header(to_email, 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 连接SMTP服务器
        server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'])
        server.login(config['email'], config['password'])
        
        # 发送邮件
        server.sendmail(config['email'], [to_email], msg.as_string())
        server.quit()
        
        return True, "发送成功"
    except Exception as e:
        return False, f"发送失败: {str(e)}"

def main():
    """主函数"""
    print("=== 开始测试邮件发送 ===")
    
    # 读取配置
    qq_config, mail163_config = read_email_config()
    
    # 测试邮件内容
    subject = "OpenClaw测试邮件"
    content = "hello world - 这是OpenClaw定时任务测试邮件"
    
    results = []
    
    # 发送到QQ邮箱
    print(f"发送到QQ邮箱: {qq_config['email']}")
    success, message = send_email(qq_config, qq_config['email'], subject, content)
    results.append({
        '邮箱': qq_config['email'],
        '状态': '成功' if success else '失败',
        '消息': message
    })
    
    # 发送到163邮箱
    print(f"发送到163邮箱: {mail163_config['email']}")
    success, message = send_email(mail163_config, mail163_config['email'], subject, content)
    results.append({
        '邮箱': mail163_config['email'],
        '状态': '成功' if success else '失败',
        '消息': message
    })
    
    # 输出结果
    print("\n=== 发送结果 ===")
    for result in results:
        print(f"{result['邮箱']}: {result['状态']} - {result['消息']}")
    
    # 写入结果文件
    with open('/root/.openclaw/workspace/ai_agent/results/email_test_result.txt', 'w') as f:
        f.write("邮件发送测试结果\n")
        f.write("=" * 50 + "\n")
        for result in results:
            f.write(f"邮箱: {result['邮箱']}\n")
            f.write(f"状态: {result['状态']}\n")
            f.write(f"消息: {result['消息']}\n")
            f.write("-" * 30 + "\n")
    
    print("\n✅ 测试完成！结果已保存到 email_test_result.txt")

if __name__ == "__main__":
    main()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
