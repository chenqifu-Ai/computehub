#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票价格预警监控脚本
"""

import requests
import json
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# 配置
ALERT_CONFIG = {
    "stocks": {
        "600460": {"name": "士兰微", "warning": 28.0, "support": 26.0},
        "600361": {"name": "华联股份", "warning": 2.8, "support": 2.5},
        "002594": {"name": "比亚迪", "buy": 100.0, "target": 120.0},
        "600519": {"name": "贵州茅台", "buy": 1350.0, "support": 1300.0},
        "300750": {"name": "宁德时代", "buy": 380.0, "support": 350.0},
        "000002": {"name": "万科 A", "danger": 4.0, "support": 3.8},
        "600000": {"name": "浦发银行", "danger": 9.5, "support": 9.0},
    },
    "email": {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465,
        "from_email": "19525456@qq.com",
        "to_email": "19525456@qq.com",
        "password": "xunlwhjokescbgdd"
    }
}

def get_stock_price(code):
    """获取股票价格"""
    try:
        res = requests.get(f"http://localhost:8000/api/market/quote?code={code}", timeout=5)
        data = res.json()
        if data.get("code") == 200:
            return data["data"]
    except:
        pass
    return None

def check_alert(code, name, price_data):
    """检查价格预警"""
    alerts = []
    config = ALERT_CONFIG["stocks"].get(code, {})
    
    price = price_data.get("price", 0)
    change_percent = price_data.get("change_percent", 0)
    
    # 危险价位（跌破支撑）
    if "danger" in config and price <= config["danger"]:
        alerts.append(f"🔴 {code} {name} 跌破危险位 ¥{config['danger']}！当前¥{price:.2f}")
    
    # 支撑位
    if "support" in config and abs(price - config["support"]) / config["support"] < 0.02:
        alerts.append(f"🟡 {code} {name} 接近支撑位 ¥{config['support']}！当前¥{price:.2f}")
    
    # 买入位
    if "buy" in config and price <= config["buy"]:
        alerts.append(f"🟢 {code} {name} 达到买入位 ¥{config['buy']}！当前¥{price:.2f}")
    
    # 目标位
    if "target" in config and price >= config["target"]:
        alerts.append(f"💰 {code} {name} 达到目标位 ¥{config['target']}！当前¥{price:.2f}")
    
    # 大幅下跌
    if change_percent <= -5:
        alerts.append(f"🔴 {code} {name} 暴跌 {change_percent:.2f}%！")
    
    return alerts

def send_email_alert(alerts):
    """发送邮件预警"""
    if not alerts:
        return
    
    subject = f"🚨 股票价格预警 - {datetime.now().strftime('%H:%M')}"
    
    content = f"""
股票价格预警
============
时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

预警内容:
"""
    for alert in alerts:
        content += f"- {alert}\n"
    
    content += f"""

---
请及时处理！
"""
    
    try:
        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = ALERT_CONFIG["email"]["from_email"]
        msg["To"] = ALERT_CONFIG["email"]["to_email"]
        
        server = smtplib.SMTP_SSL(ALERT_CONFIG["email"]["smtp_server"], ALERT_CONFIG["email"]["smtp_port"])
        server.login(ALERT_CONFIG["email"]["from_email"], ALERT_CONFIG["email"]["password"])
        server.sendmail(ALERT_CONFIG["email"]["from_email"], ALERT_CONFIG["email"]["to_email"], msg.as_string())
        server.quit()
        
        print(f"✅ 预警邮件已发送：{len(alerts)} 条警报")
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")

def monitor():
    """监控主函数"""
    print("=" * 60)
    print("🔍 股票价格监控启动")
    print("=" * 60)
    
    all_alerts = []
    
    for code, config in ALERT_CONFIG["stocks"].items():
        data = get_stock_price(code)
        if data:
            name = data.get("name", config["name"])
            price = data.get("price", 0)
            change = data.get("change_percent", 0)
            emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
            
            print(f"{emoji} {code} {name:8s} ¥{price:7.2f}  {change:+6.2f}%")
            
            alerts = check_alert(code, name, data)
            all_alerts.extend(alerts)
        else:
            print(f"❌ {code} 获取价格失败")
    
    print("=" * 60)
    
    if all_alerts:
        print(f"\n🚨 发现 {len(all_alerts)} 条预警:")
        for alert in all_alerts:
            print(f"  - {alert}")
        
        # 发送邮件
        send_email_alert(all_alerts)
    else:
        print("\n✅ 无预警")
    
    return all_alerts

if __name__ == "__main__":
    monitor()
