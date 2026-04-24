#!/usr/bin/env python3
"""
股票监控系统 - 开盘监控
监控A股市场开盘情况，获取主要指数和个股开盘数据
"""

import requests
import json
import time
from datetime import datetime, timedelta
import os

def get_stock_data(symbols):
    """
    获取股票实时数据
    这里使用模拟数据，实际应用中可以接入真实的股票API
    """
    # 模拟股票数据
    mock_data = {
        '000001': {'name': '上证指数', 'price': 3250.45, 'change': 15.23, 'change_percent': 0.47},
        '399001': {'name': '深证成指', 'price': 11850.67, 'change': -23.45, 'change_percent': -0.20},
        '399006': {'name': '创业板指', 'price': 2450.78, 'change': 8.92, 'change_percent': 0.37},
        '600519': {'name': '贵州茅台', 'price': 1850.00, 'change': 25.50, 'change_percent': 1.40},
        '000858': {'name': '五粮液', 'price': 158.30, 'change': -2.10, 'change_percent': -1.31}
    }
    
    result = {}
    for symbol in symbols:
        if symbol in mock_data:
            result[symbol] = mock_data[symbol]
    
    return result

def format_market_status():
    """格式化市场状态信息"""
    current_time = datetime.now()
    weekday = current_time.weekday()  # 0=Monday, 6=Sunday
    
    # A股交易时间判断
    market_hours = [
        (9, 30, 11, 30),  # 上午交易时段
        (13, 0, 15, 0)    # 下午交易时段
    ]
    
    hour = current_time.hour
    minute = current_time.minute
    
    is_trading_time = False
    for start_h, start_m, end_h, end_m in market_hours:
        if (hour > start_h or (hour == start_h and minute >= start_m)) and \
           (hour < end_h or (hour == end_h and minute <= end_m)):
            is_trading_time = True
            break
    
    if weekday >= 5:  # 周末
        status = "休市 (周末)"
    elif not is_trading_time:
        if hour < 9 or (hour == 9 and minute < 30):
            status = "未开盘"
        elif (hour == 11 and minute > 30) or (hour == 12):
            status = "午休"
        else:
            status = "已收盘"
    else:
        status = "交易中"
    
    return status, current_time.strftime("%Y-%m-%d %H:%M:%S")

def main():
    """主函数"""
    print("=== 股票监控系统 - 开盘监控 ===")
    
    # 获取市场状态
    market_status, current_time_str = format_market_status()
    print(f"当前时间: {current_time_str}")
    print(f"市场状态: {market_status}")
    
    # 定义要监控的股票代码
    symbols = ['000001', '399001', '399006', '600519', '000858']
    
    if market_status == "交易中":
        print("\n正在获取实时股票数据...")
        stock_data = get_stock_data(symbols)
        
        print("\n{:<10} {:<10} {:<10} {:<10} {:<10}".format(
            "代码", "名称", "价格", "涨跌", "涨幅%"))
        print("-" * 60)
        
        for symbol, data in stock_data.items():
            print("{:<10} {:<10} {:<10.2f} {:<10.2f} {:<10.2f}".format(
                symbol, data['name'], data['price'], 
                data['change'], data['change_percent']))
    else:
        print(f"\n当前非交易时间，市场状态为: {market_status}")
        print("下次开盘时间: 下个交易日 09:30")
    
    # 保存结果到文件
    result_dir = "/root/.openclaw/workspace/ai_agent/results"
    os.makedirs(result_dir, exist_ok=True)
    
    result_data = {
        "timestamp": current_time_str,
        "market_status": market_status,
        "monitoring_symbols": symbols
    }
    
    if market_status == "交易中":
        result_data["stock_data"] = get_stock_data(symbols)
    
    result_file = os.path.join(result_dir, f"stock_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n监控结果已保存至: {result_file}")

if __name__ == "__main__":
    main()