#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import sys

def get_stock_price_eastmoney(symbol):
    """
    使用东方财富网API获取股票价格
    """
    try:
        # 东方财富网API
        url = f"http://push2.eastmoney.com/api/qt/stock/get?secid=1.{symbol}&fields=f58,f107,f57"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and data['data'] is not None:
                price = float(data['data']['f58'])
                name = data['data']['f57']
                return price, name
    except Exception as e:
        print(f"东方财富API失败: {e}")
    
    return None, None

def get_stock_price_sina(symbol):
    """
    使用新浪股票API（备用）
    """
    try:
        url = f"https://hq.sinajs.cn/list=sh{symbol}"
        headers = {
            'Referer': 'https://finance.sina.com.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.text
            if 'var hq_str_sh' in data:
                parts = data.split('"')[1].split(',')
                if len(parts) > 3:
                    price = float(parts[3])
                    name = parts[0]
                    return price, name
    except Exception as e:
        print(f"新浪API失败: {e}")
    
    return None, None

if __name__ == "__main__":
    symbol = "601866"
    
    # 首先尝试东方财富
    price, name = get_stock_price_eastmoney(symbol)
    
    # 如果东方财富失败，尝试新浪
    if price is None:
        price, name = get_stock_price_sina(symbol)
    
    if price is not None:
        print(f"中远海发({symbol})当前股价: ¥{price:.2f}")
        if 2.50 <= price <= 2.70:
            print("ALERT: 股价在目标区间¥2.50-2.70内，建议考虑买入机会！")
        else:
            print(f"股价不在目标区间内。目标区间: ¥2.50-2.70")
            if price < 2.50:
                print(f"当前股价低于目标区间¥{2.50 - price:.2f}")
            else:
                print(f"当前股价高于目标区间¥{price - 2.70:.2f}")
    else:
        print("无法获取股票价格数据")
        sys.exit(1)