#!/usr/bin/env python3
"""
股票紧急决策脚本 - 2026-03-24 09:34
监控士兰微是否跌破止损位，实时发送卖出信号
"""

from scripts.email_utils import send_email_safe
import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header

def get_stock_price(code):
    """获取股票实时价格"""
    if code.startswith('6'):
        url = f"http://qt.gtimg.cn/q=sh{code}"
    else:
        url = f"http://qt.gtimg.cn/q=sz{code}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.text
        # 解析腾讯财经数据
        parts = data.split('~')
        if len(parts) > 3:
            return float(parts[3])
    except Exception as e:
        print(f"获取价格失败: {e}")
        return None
    return None

def send_alert(subject, message):
    """发送邮件提醒"""
    smtp_server = "smtp.qq.com"
    smtp_port = 465
    sender_email = "19525456@qq.com"
    password = "xunlwhjokescbgdd"
    receiver_email = "19525456@qq.com"
    
    msg = MIMEText(message, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败: {e}")

def main():
    print("开始监控士兰微 (600460)...")
    print("止损位: 26.00")
    
    while True:
        current_price = get_stock_price("600460")
        if current_price is not None:
            print(f"当前价格: {current_price:.2f}")
            
            if current_price <= 26.00:
                alert_msg = f"🚨 紧急卖出信号！\n\n士兰微 (600460) 当前价格: {current_price:.2f}\n已触及止损位 26.00\n建议立即卖出！"
                print(alert_msg)
                send_alert("【紧急】士兰微卖出信号", alert_msg)
                break
            elif current_price >= 28.00:
                alert_msg = f"📈 减仓信号！\n\n士兰微 (600460) 当前价格: {current_price:.2f}\n建议减仓一半锁定利润"
                print(alert_msg)
                send_alert("【减仓】士兰微减仓信号", alert_msg)
                break
            else:
                print("继续监控...")
        
        time.sleep(30)  # 每30秒检查一次

if __name__ == "__main__":
    main()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
