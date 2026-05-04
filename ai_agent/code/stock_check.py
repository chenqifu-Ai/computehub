#!/usr/bin/env python3
"""
获取股票实时数据 - 使用多个数据源
"""

import requests
import json
from datetime import datetime

POSITIONS = [
    {"name": "士兰微", "code": "600460", "volume": 1000, "cost": 29.364},
    {"name": "华联股份", "code": "000882", "volume": 22600, "cost": 1.779},
]

def get_price_tencent(code):
    """腾讯财经接口"""
    # 腾讯需要加前缀
    prefix = "sh" if code.startswith("6") else "sz"
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = "gbk"
        data = response.text
        
        if '~' in data:
            parts = data.split('~')
            if len(parts) >= 45:
                return {
                    "name": parts[1],
                    "current": float(parts[3]),
                    "prev_close": float(parts[4]),
                    "open": float(parts[5]),
                    "high": float(parts[33]) if len(parts) > 33 else float(parts[3]),
                    "low": float(parts[34]) if len(parts) > 34 else float(parts[3]),
                }
    except Exception as e:
        print(f"腾讯接口失败: {e}")
    return None

def get_price_eastmoney(code):
    """东方财富接口"""
    # 东财需要加前缀
    prefix = "1." if code.startswith("6") else "0."
    url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={prefix}{code}&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if data.get("data") and data["data"].get("f43"):
            d = data["data"]
            return {
                "name": "",
                "current": d["f43"] / 100 if d.get("f43") else 0,
                "prev_close": d["f46"] / 100 if d.get("f46") else 0,
                "open": d["f47"] / 100 if d.get("f47") else 0,
                "high": d["f44"] / 100 if d.get("f44") else 0,
                "low": d["f45"] / 100 if d.get("f45") else 0,
            }
    except Exception as e:
        print(f"东方财富接口失败: {e}")
    return None

def get_stock_price(code):
    """尝试多个数据源"""
    # 先试东方财富
    data = get_price_eastmoney(code)
    if data and data.get("current", 0) > 0:
        return data
    
    # 再试腾讯
    data = get_price_tencent(code)
    if data and data.get("current", 0) > 0:
        return data
    
    return None

def analyze():
    """分析持仓"""
    print("="*60)
    print("📊 股票实时分析")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    total_cost = 0
    total_value = 0
    
    for pos in POSITIONS:
        print(f"\n【{pos['name']} {pos['code']}】")
        price = get_stock_price(pos["code"])
        
        if price and price.get("current", 0) > 0:
            current = price["current"]
            cost = pos["cost"]
            volume = pos["volume"]
            
            profit = (current - cost) * volume
            profit_pct = (current - cost) / cost * 100
            today_change = (current - price["prev_close"]) / price["prev_close"] * 100 if price["prev_close"] > 0 else 0
            
            print(f"  当前价: ¥{current:.2f}")
            print(f"  成本价: ¥{cost:.2f}")
            print(f"  持仓盈亏: ¥{profit:,.2f} ({profit_pct:+.2f}%)")
            print(f"  今日涨跌: {today_change:+.2f}%")
            
            total_cost += cost * volume
            total_value += current * volume
            
            # 操作建议
            print(f"  ──────────────")
            if pos["code"] == "600460":  # 士兰微
                if current >= 32.0:
                    print("  ⚠️ 接近止盈位，考虑止盈50%")
                elif current <= 26.0:
                    print("  🔴 触及止损位，建议止损")
                elif profit_pct > 5:
                    print("  🟢 盈利良好，继续持有")
                else:
                    print("  🟡 持有观望")
            
            elif pos["code"] == "000882":  # 华联股份
                if current <= 1.40:
                    print("  🔴 触及止损位，建议止损")
                elif current >= 2.00:
                    print("  ⚠️ 接近止盈位，考虑止盈50%")
                elif profit_pct < -10:
                    print("  🟡 深度亏损，等反弹")
                else:
                    print("  🟡 持有观望")
        else:
            print(f"  ❌ 获取数据失败")
            total_cost += pos["cost"] * pos["volume"]
    
    print("\n" + "="*60)
    print("💰 总持仓")
    print("="*60)
    if total_cost > 0:
        total_profit = total_value - total_cost
        print(f"总成本: ¥{total_cost:,.2f}")
        print(f"总市值: ¥{total_value:,.2f}")
        print(f"总盈亏: ¥{total_profit:,.2f} ({total_profit/total_cost*100:+.2f}%)")
    else:
        print("无法获取实时数据")

if __name__ == "__main__":
    analyze()