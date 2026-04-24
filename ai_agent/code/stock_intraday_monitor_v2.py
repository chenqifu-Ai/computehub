#!/usr/bin/env python3
"""
股票监控系统 - 盘中任务 (改进版)
执行时间: 交易时间内 (9:30-15:00)
"""

import requests
import sys
import json
import time
from datetime import datetime, time as dt_time
import os

def get_stock_price(stock_code):
    """获取股票价格"""
    try:
        if stock_code.startswith('6'):
            prefix = 'sh'
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            prefix = 'sz'
        else:
            prefix = 'sh'
        
        url = f"https://hq.sinajs.cn/list={prefix}{stock_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gb2312'
        
        data = response.text
        if 'var hq_str_' in data and '=' in data:
            stock_data = data.split('="')[1].split('"')[0]
            parts = stock_data.split(',')
            
            if len(parts) > 3:
                return {
                    'name': parts[0],
                    'price': float(parts[3]),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        return None
    except Exception as e:
        return None

def check_hualian_alert(current_price):
    """检查华联股份是否需要预警"""
    stop_loss = 1.60
    alert_levels = {
        'critical': 1.61,  # 距离止损0.6%
        'warning': 1.63,   # 距离止损1.9%
        'monitor': 1.65    # 距离止损3.1%
    }
    
    alerts = []
    if current_price <= alert_levels['critical']:
        alerts.append('CRITICAL')
    elif current_price <= alert_levels['warning']:
        alerts.append('WARNING')
    elif current_price <= alert_levels['monitor']:
        alerts.append('MONITOR')
    
    return alerts

def check_cosco_opportunity(current_price):
    """检查中远海发买入机会"""
    target_min = 2.50
    target_max = 2.70
    
    if target_min <= current_price <= target_max:
        return True
    return False

def send_alert(message, level='INFO'):
    """发送提醒到日志文件"""
    alert_file = f"/root/.openclaw/workspace/memory/{datetime.now().strftime('%Y-%m-%d')}-stock-alerts.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(alert_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")
    
    print(f"[{timestamp}] [{level}] {message}")

def is_trading_hours():
    """检查是否在交易时间内"""
    now = datetime.now().time()
    trading_start = dt_time(9, 30)
    trading_end = dt_time(15, 0)
    
    # A股交易时间：9:30-11:30, 13:00-15:00
    morning_session = trading_start <= now <= dt_time(11, 30)
    afternoon_session = dt_time(13, 0) <= now <= trading_end
    
    return morning_session or afternoon_session

def generate_status_report():
    """生成当前状态报告"""
    hualian_data = get_stock_price("000882")
    cosco_data = get_stock_price("601866")
    
    report = f"📊 股票监控状态报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    if hualian_data:
        alerts = check_hualian_alert(hualian_data['price'])
        alert_status = ' | '.join(alerts) if alerts else '正常'
        report += f"华联股份(000882): ¥{hualian_data['price']:.2f} [{alert_status}]\n"
    else:
        report += "华联股份: 数据获取失败\n"
    
    if cosco_data:
        in_range = check_cosco_opportunity(cosco_data['price'])
        range_status = '买入区间 ✅' if in_range else '等待回调 ⏳'
        report += f"中远海发(601866): ¥{cosco_data['price']:.2f} [{range_status}]\n"
    else:
        report += "中远海发: 数据获取失败\n"
    
    return report

def main():
    print("🔍 启动股票监控系统 - 盘中任务 (改进版)...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始状态报告
    print("\n" + generate_status_report())
    
    last_hualian_price = None
    last_cosco_price = None
    check_count = 0
    
    while True:
        try:
            check_count += 1
            
            # 检查是否还在交易时间
            if not is_trading_hours():
                print("🕒 非交易时间，暂停监控...")
                send_alert("交易时间结束，监控系统暂停", "INFO")
                break
            
            # 每10次检查输出一次状态报告
            if check_count % 10 == 0:
                print(generate_status_report())
            
            # 获取华联股份价格
            hualian_data = get_stock_price("000882")
            if hualian_data:
                current_hualian = hualian_data['price']
                
                # 检查价格变化和预警
                if last_hualian_price is None or abs(current_hualian - last_hualian_price) >= 0.01:
                    alerts = check_hualian_alert(current_hualian)
                    if alerts:
                        for alert in alerts:
                            if alert == 'CRITICAL':
                                send_alert(f"华联股份价格¥{current_hualian:.2f}，接近止损位¥1.60！立即关注！", "CRITICAL")
                            elif alert == 'WARNING':
                                send_alert(f"华联股份价格¥{current_hualian:.2f}，进入预警区间", "WARNING")
                            elif alert == 'MONITOR':
                                send_alert(f"华联股份价格¥{current_hualian:.2f}，需要加强监控", "MONITOR")
                    
                    last_hualian_price = current_hualian
            
            # 获取中远海发价格
            cosco_data = get_stock_price("601866")
            if cosco_data:
                current_cosco = cosco_data['price']
                
                # 检查买入机会
                if last_cosco_price is None or abs(current_cosco - last_cosco_price) >= 0.01:
                    if check_cosco_opportunity(current_cosco):
                        send_alert(f"中远海发价格¥{current_cosco:.2f}，进入买入区间¥2.50-2.70！考虑建仓", "OPPORTUNITY")
                    
                    last_cosco_price = current_cosco
            
            # 每30秒检查一次
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n⏹️  监控已停止")
            send_alert("用户手动停止监控", "INFO")
            break
        except Exception as e:
            print(f"❌ 监控错误: {e}")
            send_alert(f"监控系统错误: {e}", "ERROR")
            time.sleep(60)  # 错误时等待更长时间

if __name__ == "__main__":
    main()