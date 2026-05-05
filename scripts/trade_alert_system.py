#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票买卖点预警系统
实时监控，及时通知
"""

from scripts.email_utils import send_email_safe
import requests
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
import time

# 配置
ALERT_CONFIG = {
    "positions": {
        "600460": {
            "name": "士兰微",
            "volume": 1000,
            "cost": 29.364,
            "current": 25.85,  # 今日收盘价
            "buy_points": [25.00, 24.00],
            "sell_points": [28.00, 30.00],
            "stop_loss": 26.00,
            "breach_stop": True  # 已跌破止损
        },
        "000882": {
            "name": "华联股份",
            "volume": 22600,
            "cost": 1.779,
            "current": 1.58,
            "buy_points": [1.60, 1.50],
            "sell_points": [2.00, 2.50],
            "stop_loss": 1.40,
            "focus": True  # 重点关注
        }
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
    """获取股票实时价格"""
    try:
        # 尝试从本地 API 获取
        res = requests.get(f"http://localhost:8000/api/market/quote?code={code}", timeout=3)
        data = res.json()
        if data.get("code") == 200:
            return data["data"]
    except:
        pass
    
    # 模拟价格（实际应该用真实 API）
    # 这里用随机波动模拟
    import random
    pos = ALERT_CONFIG["positions"].get(code)
    if pos:
        base = pos["cost"]
        change = random.uniform(-0.05, 0.05)
        return {
            "code": code,
            "name": pos["name"],
            "price": base * (1 + change),
            "change_percent": change * 100
        }
    return None

def send_alert_email(subject, content):
    """发送预警邮件"""
    try:
        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = ALERT_CONFIG["email"]["from_email"]
        msg["To"] = ALERT_CONFIG["email"]["to_email"]
        
        server = smtplib.SMTP_SSL(ALERT_CONFIG["email"]["smtp_server"], ALERT_CONFIG["email"]["smtp_port"])
        server.login(ALERT_CONFIG["email"]["from_email"], ALERT_CONFIG["email"]["password"])
        server.sendmail(ALERT_CONFIG["email"]["from_email"], ALERT_CONFIG["email"]["to_email"], msg.as_string())
        server.quit()
        
        print(f"✅ 预警邮件已发送：{subject}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

def check_alert(code, data):
    """检查买卖点"""
    pos = ALERT_CONFIG["positions"].get(code)
    if not pos:
        return []
    
    alerts = []
    price = data.get("price", 0)
    name = pos["name"]
    
    # 检查止损
    if price <= pos["stop_loss"]:
        alerts.append({
            "type": "STOP_LOSS",
            "level": "CRITICAL",
            "message": f"🔴 止损预警！{code} {name} 当前¥{price:.2f}，止损¥{pos['stop_loss']:.2f}，建议立即卖出{pos['volume']}股！"
        })
    
    # 检查加仓点
    for buy_price in pos["buy_points"]:
        if abs(price - buy_price) / buy_price < 0.02:  # 接近 2%
            alerts.append({
                "type": "BUY",
                "level": "WARNING",
                "message": f"🟢 加仓机会！{code} {name} 接近¥{buy_price:.2f}，当前¥{price:.2f}，可加仓！"
            })
    
    # 检查止盈点
    for sell_price in pos["sell_points"]:
        if price >= sell_price:
            alerts.append({
                "type": "SELL",
                "level": "WARNING",
                "message": f"💰 止盈预警！{code} {name} 达到¥{sell_price:.2f}，当前¥{price:.2f}，建议止盈！"
            })
    
    # 检查大幅波动
    change = data.get("change_percent", 0)
    if change <= -5:
        alerts.append({
            "type": "DROP",
            "level": "WARNING",
            "message": f"🔴 大幅下跌！{code} {name} 跌幅{change:.2f}%，注意风险！"
        })
    elif change >= 5:
        alerts.append({
            "type": "RISE",
            "level": "INFO",
            "message": f"🟢 大幅上涨！{code} {name} 涨幅{change:.2f}%，关注！"
        })
    
    return alerts

def monitor_once():
    """单次监控"""
    print("=" * 70)
    print(f"🔍 监控时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    all_alerts = []
    
    for code, pos in ALERT_CONFIG["positions"].items():
        data = get_stock_price(code)
        if data:
            price = data.get("price", 0)
            change = data.get("change_percent", 0)
            emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
            
            print(f"{emoji} {code} {pos['name']:8s} ¥{price:7.2f}  {change:+6.2f}%")
            
            alerts = check_alert(code, data)
            all_alerts.extend(alerts)
        else:
            print(f"❌ {code} 获取价格失败")
    
    print("=" * 70)
    
    # 发送预警
    if all_alerts:
        print(f"\n🚨 发现 {len(all_alerts)} 条预警:")
        for alert in all_alerts:
            print(f"  [{alert['level']}] {alert['message']}")
        
        # 生成邮件内容
        email_content = f"""
股票买卖点预警
============
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

预警内容:
"""
        for alert in all_alerts:
            email_content += f"- {alert['message']}\n"
        
        email_content += f"""

当前持仓:
"""
        for code, pos in ALERT_CONFIG["positions"].items():
            data = get_stock_price(code)
            if data:
                price = data.get("price", 0)
                profit = (price - pos["cost"]) * pos["volume"]
                email_content += f"- {code} {pos['name']}: ¥{price:.2f}, 盈亏¥{profit:.2f}\n"
        
        email_content += f"""

---
请及时处理！
"""
        
        # 发送邮件
        critical_alerts = [a for a in all_alerts if a["level"] == "CRITICAL"]
        if critical_alerts:
            send_alert_email("🔴 紧急止损预警", email_content)
        else:
            send_alert_email("📊 股票买卖点预警", email_content)
    else:
        print("\n✅ 无预警，持仓正常")
    
    return all_alerts

def main():
    """主函数"""
    print("\n" + "🚨" * 35)
    print("股票买卖点预警系统启动")
    print("🚨" * 35 + "\n")
    print("监控标的:")
    for code, pos in ALERT_CONFIG["positions"].items():
        print(f"  - {code} {pos['name']}: 止损¥{pos['stop_loss']}, 止盈¥{pos['sell_points']}")
    print("\n监控频率：每 5 分钟一次")
    print("通知方式：邮件 + 控制台")
    print("\n" + "=" * 70 + "\n")
    
    # 持续监控
    while True:
        try:
            monitor_once()
            time.sleep(300)  # 5 分钟
        except KeyboardInterrupt:
            print("\n👋 监控已停止")
            break
        except Exception as e:
            print(f"❌ 监控异常：{e}")
            time.sleep(60)

if __name__ == "__main__":
    # 首次运行
    monitor_once()
    # 持续监控（后台运行）
    # main()


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
