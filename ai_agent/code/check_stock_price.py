import requests
import json
import sys

def get_stock_price(stock_code):
    """
    获取股票价格 - 尝试多种可能的数据源
    """
    # 尝试使用腾讯财经API
    try:
        url = f"http://qt.gtimg.cn/q=s_sh{stock_code}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.text
            if data.startswith('v_'):
                parts = data.split('~')
                if len(parts) > 3:
                    price = float(parts[3])
                    return price
    except Exception as e:
        print(f"腾讯财经API失败: {e}")
    
    # 尝试使用网易财经API
    try:
        url = f"http://api.money.126.net/data/feed/0{stock_code},money.api"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.text
            # 网易返回的是JSONP格式
            json_str = data[data.find('{'):data.rfind('}')+1]
            if json_str:
                stock_data = json.loads(json_str)
                if f"0{stock_code}" in stock_data:
                    price = stock_data[f"0{stock_code}"]["price"]
                    return float(price)
    except Exception as e:
        print(f"网易财经API失败: {e}")
    
    return None

if __name__ == "__main__":
    stock_code = "601866"
    price = get_stock_price(stock_code)
    if price is not None:
        print(f"中远海发({stock_code})当前股价: ¥{price:.2f}")
        if 2.50 <= price <= 2.70:
            print("ALERT: 股价在目标区间内(¥2.50-2.70)，建议考虑买入机会！")
        else:
            print(f"股价不在目标区间内。目标区间: ¥2.50-2.70")
    else:
        print("无法获取股票价格数据")
        sys.exit(1)