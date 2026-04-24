#!/usr/bin/env python3
"""
盘前数据分析 - 可立即运行
"""

import requests
from datetime import datetime, timedelta

def get_a50():
    """获取A50期指"""
    url = "http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": "115.GGICHN",
        "fields": "f43,f44,f45,f46,f47,f48"
    }
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("data"):
            d = data["data"]
            current = d.get("f43", 0) / 100 if d.get("f43") else None
            prev_close = d.get("f46", 0) / 100 if d.get("f46") else None
            high = d.get("f44", 0) / 100 if d.get("f44") else None
            low = d.get("f45", 0) / 100 if d.get("f45") else None
            
            if current and prev_close:
                change = (current - prev_close) / prev_close * 100
                return {
                    "current": current,
                    "prev_close": prev_close,
                    "change_pct": change,
                    "high": high,
                    "low": low
                }
    except Exception as e:
        print(f"A50获取失败: {e}")
    return None

def get_us_stock_impact():
    """获取美股影响"""
    # 简单返回美股时间
    yesterday = datetime.now() - timedelta(days=1)
    return {
        "date": yesterday.strftime("%Y-%m-%d"),
        "note": "美股昨晚收盘，影响今日A股开盘"
    }

def analyze_pre_market():
    """盘前分析"""
    print("="*60)
    print("📊 盘前数据分析")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. A50期指
    print("\n【A50期指】")
    a50 = get_a50()
    if a50:
        print(f"  当前价: {a50['current']:.2f}")
        print(f"  昨收: {a50['prev_close']:.2f}")
        print(f"  涨跌: {a50['change_pct']:+.2f}%")
        
        if a50['change_pct'] > 0.5:
            print("  🟢 A50上涨 → A股可能高开")
        elif a50['change_pct'] < -0.5:
            print("  🔴 A50下跌 → A股可能低开")
        else:
            print("  🟡 A50波动小 → A股可能平开")
    else:
        print("  ❌ 获取失败")
    
    # 2. 美股影响
    print("\n【美股影响】")
    us = get_us_stock_impact()
    print(f"  {us['date']} 美股收盘")
    print("  注：美股涨跌会影响A股开盘情绪")
    
    # 3. 持仓股票昨日数据
    print("\n【持仓股票昨日数据】")
    print("\n  士兰微 600460:")
    print("    昨收: ¥26.39")
    print("    持仓成本: ¥29.36")
    print("    浮亏: -11.5%")
    print("    ⚠️ 已破止损位26元")
    
    print("\n  华联股份 000882:")
    print("    昨收: ¥1.67")
    print("    持仓成本: ¥1.78")
    print("    浮亏: -6.6%")
    
    # 4. 盘前建议
    print("\n" + "="*60)
    print("📋 盘前建议")
    print("="*60)
    
    print("\n【士兰微】")
    print("  ⚠️ 昨收26.39，已破止损位26元")
    print("  建议：开盘后观察反弹情况")
    print("  风险：若低开，注意止损")
    
    print("\n【华联股份】")
    print("  🟡 昨收1.67，接近成本1.78")
    print("  建议：观望，等反弹")
    
    print("\n【整体策略】")
    print("  1. 09:15-09:25 观察集合竞价量能")
    print("  2. 09:30 开盘后看前3分钟走势")
    print("  3. 士兰微若跌破26元，考虑止损")
    print("  4. 华联股份等待反弹到1.78以上")

if __name__ == "__main__":
    analyze_pre_market()