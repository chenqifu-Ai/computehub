import urllib.request
import json
import ssl

# 忽略SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context

def get_stock_price():
    try:
        # 尝试使用腾讯财经API
        url = "https://qt.gtimg.cn/q=s_sh601866"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = response.read().decode('gbk')
        
        # 解析数据
        if data.startswith('v_s_sh601866="'):
            parts = data.split('~')
            if len(parts) > 3:
                price = parts[3]
                print(f"中远海发(601866)当前股价: ¥{price}")
                return float(price)
    except Exception as e:
        print(f"腾讯财经API错误: {e}")
    
    try:
        # 尝试使用新浪API
        url = "http://hq.sinajs.cn/list=sh601866"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = response.read().decode('gbk')
        
        # 解析数据
        if '="' in data:
            parts = data.split('"')[1].split(',')
            if len(parts) > 3:
                price = parts[3]
                print(f"中远海发(601866)当前股价: ¥{price}")
                return float(price)
    except Exception as e:
        print(f"新浪API错误: {e}")
    
    print("无法获取中远海发(601866)的当前股价")
    return None

if __name__ == "__main__":
    price = get_stock_price()
    if price is not None:
        if 2.50 <= price <= 2.70:
            print("⚠️ 股价在目标区间内！建议老大考虑买入机会")
        else:
            print(f"当前股价不在¥2.50-2.70目标区间内")
    else:
        print("无法确定是否在目标区间内")