#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单股票价格检查 - 使用公开API
"""

import json
import urllib.request
import urllib.error

def get_stock_price_from_api():
    """尝试从多个免费API获取股票价格"""
    
    # 尝试使用 Alpha Vantage (如果可用)
    # 注意：这需要API密钥，所以可能不工作
    
    # 尝试使用 FMP (Financial Modeling Prep) 的免费端点
    try:
        url = "https://financialmodelingprep.com/api/v3/quote/601866.SS"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if isinstance(data, list) and len(data) > 0:
                return "中远海发", data[0].get("price", None)
    except Exception as e:
        print(f"FMP API 失败: {e}")
    
    # 尝试使用其他方法
    try:
        # 使用腾讯财经的接口（如果可用）
        url = "http://qt.gtimg.cn/q=sh601866"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('gbk')
            # 解析腾讯财经格式: v_sh601866="~中远海控~6.25~..."
            if 'v_sh601866=' in content:
                parts = content.split('"')[1].split('~')
                if len(parts) > 3:
                    name = parts[1]
                    price = float(parts[3])
                    return name, price
    except Exception as e:
        print(f"腾讯财经 API 失败: {e}")
    
    return None, None

if __name__ == "__main__":
    name, price = get_stock_price_from_api()
    
    if price is not None:
        print(f"股票名称: {name}")
        print(f"当前价格: ¥{price:.2f}")
        print(f"目标区间: ¥2.50 - ¥2.70")
        
        if 2.50 <= price <= 2.70:
            print("✅ 股价在目标区间内！建议考虑买入机会。")
        elif price < 2.50:
            print(f"💰 股价低于目标区间 ¥{2.50-price:.2f}，可能有更好的买入机会。")
        else:
            print(f"📈 股价高于目标区间 ¥{price-2.70:.2f}，等待回调。")
    else:
        print("❌ 无法获取股票价格信息，请稍后重试。")
        print("建议手动检查中远海发(601866)的实时股价。")