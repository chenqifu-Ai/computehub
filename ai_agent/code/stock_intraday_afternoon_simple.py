#!/usr/bin/env python3
"""
股票监控系统 - 下午盘中简单版
执行时间: 下午交易时间 (13:00-15:00)
只执行一次数据获取和报告生成
"""

import requests
import json
from datetime import datetime

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

def generate_afternoon_report():
    """生成下午盘中监控报告"""
    hualian_data = get_stock_price("000882")
    cosco_data = get_stock_price("601866")
    
    report_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "task": "stock_intraday_afternoon_monitor",
        "stocks": {}
    }
    
    full_report = f"📊 股票监控状态报告 - 下午盘中\n📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    if hualian_data:
        alerts = check_hualian_alert(hualian_data['price'])
        alert_status = ' | '.join(alerts) if alerts else '正常'
        full_report += f"华联股份(000882): ¥{hualian_data['price']:.2f} [{alert_status}]\n"
        report_data["stocks"]["hualian"] = {
            "code": "000882",
            "name": hualian_data['name'],
            "price": hualian_data['price'],
            "alerts": alerts
        }
    else:
        full_report += "华联股份: 数据获取失败\n"
        report_data["stocks"]["hualian"] = {"error": "数据获取失败"}
    
    if cosco_data:
        in_range = check_cosco_opportunity(cosco_data['price'])
        range_status = '买入区间 ✅' if in_range else '等待回调 ⏳'
        full_report += f"中远海发(601866): ¥{cosco_data['price']:.2f} [{range_status}]\n"
        report_data["stocks"]["cosco"] = {
            "code": "601866",
            "name": cosco_data['name'],
            "price": cosco_data['price'],
            "in_buy_range": in_range
        }
    else:
        full_report += "中远海发: 数据获取失败\n"
        report_data["stocks"]["cosco"] = {"error": "数据获取失败"}
    
    # 添加下午盘特别提醒
    full_report += "\n💡 下午盘注意事项:\n"
    full_report += "• 关注尾盘资金流向和成交量变化\n"
    full_report += "• 注意主力资金是否护盘或出货\n"
    full_report += "• 如有持仓，考虑是否需要调整止盈止损位\n"
    
    report_data["full_report"] = full_report
    
    return report_data

def main():
    print("🔍 执行股票监控系统 - 下午盘中任务...")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取数据并生成报告
    report_data = generate_afternoon_report()
    
    # 保存结果
    result_dir = "/root/.openclaw/workspace/ai_agent/results"
    import os
    os.makedirs(result_dir, exist_ok=True)
    
    result_file = f"{result_dir}/stock_intraday_afternoon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print("✅ 报告生成完成")
    print("\n" + "="*50)
    print(report_data["full_report"])
    print("="*50)
    print(f"\n📄 结果已保存到: {result_file}")

if __name__ == "__main__":
    main()