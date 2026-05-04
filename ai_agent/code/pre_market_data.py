#!/usr/bin/env python3
"""
查找盘前数据源
"""

import requests
from datetime import datetime

def check_data_sources():
    """检查各种盘前数据源"""
    print("="*60)
    print("📊 盘前数据源检查")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    sources = []
    
    # 1. 东方财富 - 盘前数据
    print("\n【东方财富】")
    try:
        # 盘前公告
        url = "http://data.eastmoney.com/notice/notice.html"
        print(f"  盘前公告: {url}")
        
        # 资金流向
        url = "http://data.eastmoney.com/zjlx/"
        print(f"  资金流向: {url}")
        
        # 龙虎榜
        url = "http://data.eastmoney.com/stock/lhb.html"
        print(f"  龙虎榜: {url}")
        
        sources.append("东方财富盘前数据")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 2. 新浪财经 - 盘前
    print("\n【新浪财经】")
    try:
        # 盘前快讯
        url = "https://finance.sina.com.cn/realstock/company/sh000001/nc.shtml"
        print(f"  盘前快讯: {url}")
        sources.append("新浪盘前快讯")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 3. 同花顺 - 盘前
    print("\n【同花顺】")
    try:
        url = "http://www.10jqka.com.cn/"
        print(f"  盘前资讯: {url}")
        sources.append("同花顺盘前资讯")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 4. 集思录 - 盘前
    print("\n【集思录】")
    try:
        url = "https://www.jisilu.cn/"
        print(f"  可转债/股票数据: {url}")
        sources.append("集思录")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 5. 腾讯财经
    print("\n【腾讯财经】")
    try:
        url = "https://gu.qq.com/"
        print(f"  盘前数据: {url}")
        sources.append("腾讯盘前数据")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 6. A股时间说明
    print("\n" + "="*60)
    print("⏰ A股交易时间")
    print("="*60)
    print("  09:15-09:20  集合竞价（可撤单）")
    print("  09:20-09:25  集合竞价（不可撤单）")
    print("  09:25-09:30  休市")
    print("  09:30-11:30  上午连续竞价")
    print("  13:00-15:00  下午连续竞价")
    
    # 7. 可获取的盘前数据
    print("\n" + "="*60)
    print("📊 可获取的盘前数据（开盘前）")
    print("="*60)
    print("  ✅ 昨日收盘数据")
    print("  ✅ 昨日龙虎榜")
    print("  ✅ 北向资金流向")
    print("  ✅ 美股收盘影响")
    print("  ✅ A50期指")
    print("  ✅ 盘前公告/新闻")
    print("  ⏳ 集合竞价数据 (09:15后)")
    
    return sources

def check_a50():
    """检查A50期指"""
    print("\n" + "="*60)
    print("📈 A50期指（影响开盘）")
    print("="*60)
    
    # A50期指接口
    url = "http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": "115.GGICHN",  # A50期指
        "fields": "f43,f44,f45,f46,f47,f48"
    }
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data.get("data"):
            d = data["data"]
            current = d.get("f43", 0) / 100 if d.get("f43") else None
            prev_close = d.get("f46", 0) / 100 if d.get("f46") else None
            
            if current and prev_close:
                change = (current - prev_close) / prev_close * 100
                print(f"  A50当前: {current:.2f}")
                print(f"  涨跌幅: {change:+.2f}%")
                print(f"  影响A股开盘方向")
                return current, change
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
    
    return None, None

def main():
    sources = check_data_sources()
    print("\n" + "="*60)
    print(f"✅ 可用数据源: {len(sources)}个")
    print("="*60)
    
    # 尝试获取A50
    check_a50()

if __name__ == "__main__":
    main()