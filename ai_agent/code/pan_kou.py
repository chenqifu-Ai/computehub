#!/usr/bin/env python3
"""
获取盘口数据 - 集合竞价/盘前数据
"""

import requests
import json
from datetime import datetime

POSITIONS = [
    {"name": "士兰微", "code": "600460"},
    {"name": "华联股份", "code": "000882"},
]

def get_pan_kou_eastmoney(code):
    """获取东方财富盘口数据"""
    prefix = "1." if code.startswith("6") else "0."
    url = f"http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"{prefix}{code}",
        "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f60,f170,f171,f51,f52"
    }
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data.get("data"):
            d = data["data"]
            result = {
                "current": d.get("f43", 0) / 100 if d.get("f43") else 0,
                "prev_close": d.get("f46", 0) / 100 if d.get("f46") else 0,
                "open": d.get("f47", 0) / 100 if d.get("f47") else 0,
                "high": d.get("f44", 0) / 100 if d.get("f44") else 0,
                "low": d.get("f45", 0) / 100 if d.get("f45") else 0,
                "volume": d.get("f47", 0),  # 成交量
                "amount": d.get("f48", 0),  # 成交额
            }
            return result
    except Exception as e:
        print(f"东财接口失败: {e}")
    return None

def get_bid_ask_sina(code):
    """获取新浪盘口数据（买卖五档）"""
    url = f"http://hq.sinajs.cn/list={code}"
    try:
        headers = {
            "Referer": "http://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = "gbk"
        data = response.text
        
        if 'hq_str_' in data:
            parts = data.split('"')[1].split(',')
            if len(parts) >= 32:
                # 买卖盘口数据
                bid_prices = [parts[i] for i in range(9, 14)]  # 买1-5价
                bid_volumes = [parts[i] for i in range(14, 19)]  # 买1-5量
                ask_prices = [parts[i] for i in range(19, 24)]  # 卖1-5价
                ask_volumes = [parts[i] for i in range(24, 29)]  # 卖1-5量
                
                return {
                    "name": parts[0],
                    "current": float(parts[3]),
                    "bid1_price": float(bid_prices[0]) if bid_prices[0] else 0,
                    "bid1_vol": int(bid_volumes[0]) if bid_volumes[0] else 0,
                    "bid2_price": float(bid_prices[1]) if bid_prices[1] else 0,
                    "bid2_vol": int(bid_volumes[1]) if bid_volumes[1] else 0,
                    "ask1_price": float(ask_prices[0]) if ask_prices[0] else 0,
                    "ask1_vol": int(ask_volumes[0]) if ask_volumes[0] else 0,
                    "ask2_price": float(ask_prices[1]) if ask_prices[1] else 0,
                    "ask2_vol": int(ask_volumes[1]) if ask_volumes[1] else 0,
                }
    except Exception as e:
        print(f"新浪接口失败: {e}")
    return None

def get_pre_market(code):
    """获取盘前/集合竞价数据"""
    # 东方财富集合竞价数据
    prefix = "1." if code.startswith("6") else "0."
    url = "http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"{prefix}{code}",
        "fields": "f43,f46,f47,f48,f49,f50,f51,f52,f60,f169,f170"
    }
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data.get("data"):
            d = data["data"]
            return {
                "current": d.get("f43", 0) / 100 if d.get("f43") else None,
                "prev_close": d.get("f46", 0) / 100 if d.get("f46") else None,
            }
    except Exception as e:
        print(f"盘前数据获取失败: {e}")
    return None

def analyze_pan_kou():
    """分析盘口"""
    print("="*60)
    print("📊 盘口数据分析")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    print("\n⚠️ 当前时间: 08:05")
    print("状态: 盘前（集合竞价: 09:15-09:25，开盘: 09:30）")
    print("盘口数据需等到 09:15 集合竞价开始后才有")
    
    for pos in POSITIONS:
        print(f"\n{'='*50}")
        print(f"【{pos['name']} {pos['code']}】")
        print(f"{'='*50}")
        
        # 尝试获取数据
        print("\n📡 尝试获取数据...")
        
        # 新浪盘口
        print("\n新浪财经接口:")
        sina_data = get_bid_ask_sina(pos["code"])
        if sina_data and sina_data.get("current", 0) > 0:
            print(f"  当前价: ¥{sina_data['current']:.2f}")
            if sina_data.get("bid1_price", 0) > 0:
                print(f"  买一: ¥{sina_data['bid1_price']:.2f} × {sina_data['bid1_vol']}")
            if sina_data.get("ask1_price", 0) > 0:
                print(f"  卖一: ¥{sina_data['ask1_price']:.2f} × {sina_data['ask1_vol']}")
            print("  ✅ 盘口数据获取成功")
        else:
            print("  ❌ 无盘口数据（盘前时段）")
        
        # 东方财富
        print("\n东方财富接口:")
        east_data = get_pan_kou_eastmoney(pos["code"])
        if east_data and east_data.get("current", 0) > 0:
            print(f"  当前价: ¥{east_data['current']:.2f}")
            print(f"  昨收: ¥{east_data['prev_close']:.2f}")
            if east_data.get("open", 0) > 0:
                print(f"  今开: ¥{east_data['open']:.2f}")
            print("  ✅ 数据获取成功")
        else:
            print("  ❌ 无实时数据")
        
        # 盘前预估
        print("\n📈 盘前预估:")
        print("  集合竞价开始时间: 09:15")
        print("  集合竞价结束时间: 09:25")
        print("  开盘时间: 09:30")
        print("  建议: 09:15后获取集合竞价数据")

if __name__ == "__main__":
    analyze_pan_kou()