import requests
import json
import re

def get_stock_price(symbol):
    """获取股票价格"""
    try:
        # 尝试使用腾讯财经API
        url = f"http://qt.gtimg.cn/q={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.text
            # 解析腾讯财经返回的数据格式: v_sh601866="..."; 
            match = re.search(r'v_{}="([^"]*)"'.format(symbol), data)
            if match:
                values = match.group(1).split('~')
                if len(values) > 3:
                    price = float(values[3])  # 当前价格在第4个位置(索引3)
                    return price
    except Exception as e:
        print(f"腾讯财经API失败: {e}")
    
    try:
        # 尝试使用东方财富API
        url = f"http://push2.eastmoney.com/api/qt/stock/get?secid=1.{symbol[2:]}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and data['data'] and 'f10' in data['data']:
                price = data['data']['f10']
                return float(price)
    except Exception as e:
        print(f"东方财富API失败: {e}")
    
    return None

# 获取中远海发(601866)的股价
stock_symbol = "sh601866"
price = get_stock_price(stock_symbol)

if price is not None:
    print(f"中远海发(601866)当前股价: ¥{price:.2f}")
    if 2.50 <= price <= 2.70:
        print("股价在¥2.50-2.70区间内，建议老大考虑买入机会！")
    elif price < 2.50:
        print(f"股价低于目标区间(¥2.50)，当前价格¥{price:.2f}")
    else:
        print(f"股价高于目标区间(¥2.70)，当前价格¥{price:.2f}")
else:
    print("无法获取中远海发(601866)的股价信息")