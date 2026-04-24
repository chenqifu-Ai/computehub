#!/usr/bin/env python3
"""
股票价格监控脚本
"""

import requests
import sys
from datetime import datetime
import json

def get_stock_price(stock_code):
    """获取股票价格"""
    try:
        # 使用新浪股票API
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
        print(f"获取股价失败: {e}")
        return None

def check_price_range(stock_code, min_price, max_price):
    """检查价格是否在指定范围内"""
    stock_data = get_stock_price(stock_code)
    
    if not stock_data:
        print(f"❌ 无法获取 {stock_code} 的价格数据")
        return False
    
    current_price = stock_data['price']
    name = stock_data['name']
    
    print(f"📊 {name}({stock_code}) 当前价格: ¥{current_price}")
    
    if min_price <= current_price <= max_price:
        print(f"✅ 价格在目标区间 ¥{min_price} - ¥{max_price} 内！")
        print(f"🎯 建议：考虑买入机会")
        return True
    elif current_price < min_price:
        print(f"⬇️ 价格低于目标区间 (¥{min_price})")
        return False
    else:
        print(f"⬆️ 价格高于目标区间 (¥{max_price})")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='股票价格监控')
    parser.add_argument('--stock', required=True, help='股票代码')
    parser.add_argument('--check-range', nargs=2, type=float, metavar=('MIN', 'MAX'), 
                       help='检查价格区间，如: --check-range 2.50 2.70')
    
    args = parser.parse_args()
    
    print(f"🔍 正在检查股票 {args.stock}...")
    
    if args.check_range:
        in_range = check_price_range(args.stock, args.check_range[0], args.check_range[1])
        sys.exit(0 if in_range else 1)
    else:
        stock_data = get_stock_price(args.stock)
        if stock_data:
            print(f"\n📈 {stock_data['name']}({args.stock})")
            print(f"   当前价格: ¥{stock_data['price']}")
            print(f"   时间: {stock_data['timestamp']}")
        else:
            print("❌ 获取失败")
            sys.exit(1)

if __name__ == "__main__":
    main()
