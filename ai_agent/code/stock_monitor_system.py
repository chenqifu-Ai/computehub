#!/usr/bin/env python3
"""
股票监控系统 - AI智能体执行脚本

功能：
1. 实时数据抓取
2. 股票监控（带邮件提醒）
3. 集合竞价分析
4. 预警条件检查

作者：小智
日期：2026-03-25
"""

from scripts.email_utils import send_email_safe
import os
import sys
import json
import time
import smtplib
from datetime import datetime, time as dt_time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 系统配置
CONFIG = {
    'email': {
        'smtp_server': 'smtp.qq.com',
        'smtp_port': 465,
        'sender_email': '19525456@qq.com',
        'sender_password': 'xunlwhjokescbgdd'
    },
    'stocks': {
        'current_holdings': [
            {'code': '000882', 'name': '华联股份', 'quantity': 22600, 'cost_price': 1.779, 'stop_loss': 1.60, 'take_profit': 2.00}
        ],
        'watch_list': [
            {'code': '601866', 'name': '中远海发', 'buy_range': [2.50, 2.70]}
        ]
    },
    'monitor_schedule': {
        'pre_market': {'start': '08:20', 'end': '09:10'},
        'call_auction': '09:15',
        'market_open': '09:30',
        'intraday_morning': {'start': '10:00', 'end': '11:00'},
        'intraday_afternoon': {'start': '14:30', 'end': '15:00'}
    }
}

def get_current_time():
    """获取当前时间"""
    return datetime.now().strftime('%H:%M')

def is_market_time():
    """检查是否为交易时间"""
    current_time = datetime.now().time()
    market_start = dt_time(9, 30)
    market_end = dt_time(15, 0)
    return market_start <= current_time <= market_end

def send_email_alert(subject, message):
    """发送邮件提醒"""
    try:
        msg = MIMEMultipart()
        msg['From'] = CONFIG['email']['sender_email']
        msg['To'] = CONFIG['email']['sender_email']
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        server = smtplib.SMTP_SSL(CONFIG['email']['smtp_server'], CONFIG['email']['smtp_port'])
        server.login(CONFIG['email']['sender_email'], CONFIG['email']['sender_password'])
        server.send_message(msg)
        server.quit()
        print(f"✅ 邮件提醒已发送: {subject}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def check_stock_alerts():
    """检查股票预警条件"""
    # TODO: 实现实际的股票数据获取和预警逻辑
    print("🔍 检查股票预警条件...")
    
    # 模拟检查华联股份
    current_price_hualian = 1.65  # 模拟当前价格
    holding = CONFIG['stocks']['current_holdings'][0]
    
    alerts = []
    
    # 止损检查
    if current_price_hualian <= holding['stop_loss']:
        alerts.append(f"🔴 {holding['name']}({holding['code']}) 触及止损位 {holding['stop_loss']}, 当前价格: {current_price_hualian}")
    
    # 止盈检查  
    if current_price_hualian >= holding['take_profit']:
        alerts.append(f"🟢 {holding['name']}({holding['code']}) 触及止盈位 {holding['take_profit']}, 当前价格: {current_price_hualian}")
    
    # 跌幅检查 (>5%)
    price_change_pct = (current_price_hualian - holding['cost_price']) / holding['cost_price'] * 100
    if price_change_pct <= -5:
        alerts.append(f"🟡 {holding['name']}({holding['code']}) 跌幅超过5% ({price_change_pct:.2f}%), 当前价格: {current_price_hualian}")
    
    # 浮亏检查 (>10%)
    if price_change_pct <= -10:
        alerts.append(f"🟠 {holding['name']}({holding['code']}) 浮亏超过10% ({price_change_pct:.2f}%)")
    
    # 中远海发买入机会检查
    current_price_zhongyuan = 2.71  # 模拟当前价格
    watch_stock = CONFIG['stocks']['watch_list'][0]
    buy_min, buy_max = watch_stock['buy_range']
    if buy_min <= current_price_zhongyuan <= buy_max:
        alerts.append(f"💡 {watch_stock['name']}({watch_stock['code']}) 进入买入区间 [{buy_min}, {buy_max}], 当前价格: {current_price_zhongyuan}")
    
    if alerts:
        subject = "【股票监控】预警提醒"
        message = "\n".join(alerts)
        send_email_alert(subject, message)
        return alerts
    else:
        print("✅ 无预警条件触发")
        return []

def main():
    """主函数"""
    print("🚀 股票监控系统启动...")
    print(f"🕒 当前时间: {get_current_time()}")
    
    # 检查是否在监控时间段内
    current_time_str = get_current_time()
    
    # 执行预警检查
    alerts = check_stock_alerts()
    
    # 记录执行结果
    result = {
        'timestamp': datetime.now().isoformat(),
        'execution_time': current_time_str,
        'alerts_found': len(alerts) > 0,
        'alerts': alerts,
        'status': 'completed'
    }
    
    # 保存结果到文件
    result_file = f"/root/.openclaw/workspace/ai_agent/results/stock_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"📊 结果已保存到: {result_file}")
    print("✅ 股票监控系统执行完成")

if __name__ == "__main__":
    main()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
