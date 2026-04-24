#!/usr/bin/env python3
"""
简化的盘中股票检查脚本
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
            
            if len(parts) > 31:  # 确保有足够的数据
                return {
                    'name': parts[0],
                    'price': float(parts[3]),
                    'open': float(parts[1]),
                    'high': float(parts[4]),
                    'low': float(parts[5]),
                    'volume': int(parts[8]),
                    'amount': float(parts[9]),
                    'timestamp': f"{parts[30]} {parts[31]}"
                }
        
        return None
    except Exception as e:
        print(f"获取{stock_code}数据错误: {e}")
        return None

def main():
    stocks = ["000882", "601866"]  # 华联股份, 中远海发
    
    results = {}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for stock in stocks:
        data = get_stock_price(stock)
        results[stock] = data
    
    # 保存结果
    output = {
        "check_time": current_time,
        "stocks": results
    }
    
    with open("/root/.openclaw/workspace/ai_agent/results/stock_intraday_2026-03-31_1042.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 打印结果
    print(f"📊 盘中股票监控报告 - {current_time}")
    print("=" * 50)
    
    for stock_code, data in results.items():
        if data:
            stock_name = data['name']
            current_price = data['price']
            open_price = data['open']
            change_pct = (current_price - open_price) / open_price * 100
            
            print(f"\n{stock_name}({stock_code}):")
            print(f"  当前价: ¥{current_price:.2f}")
            print(f"  开盘价: ¥{open_price:.2f}")
            print(f"  涨跌幅: {change_pct:+.2f}%")
            print(f"  最高价: ¥{data['high']:.2f}")
            print(f"  最低价: ¥{data['low']:.2f}")
            print(f"  成交量: {data['volume']:,}")
        else:
            print(f"\n{stock_code}: 数据获取失败")
    
    return output

if __name__ == "__main__":
    main()