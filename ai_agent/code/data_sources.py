#!/usr/bin/env python3
"""
测试各种免费数据源
"""

import requests
from datetime import datetime

def test_eastmoney():
    """测试东方财富"""
    print("【东方财富】")
    print("  网站: http://www.eastmoney.com/")
    print("  数据: 免费，无需账号")
    print("  包含: 实时行情、资金流向、龙虎榜、北向资金")
    
    # 测试接口
    url = "http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": "1.000001",  # 上证指数
        "fields": "f43,f46,f47,f48"
    }
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data.get("data"):
            d = data["data"]
            current = d.get("f43", 0) / 100
            print(f"  ✅ 接口可用")
            print(f"  上证指数: {current:.2f}")
            return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    return False

def test_sina():
    """测试新浪财经"""
    print("\n【新浪财经】")
    print("  网站: https://finance.sina.com.cn/")
    print("  数据: 免费，无需账号")
    print("  包含: 实时行情、盘口五档")
    
    # 测试接口
    url = "http://hq.sinajs.cn/list=s_sh000001"
    
    try:
        headers = {
            "Referer": "http://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = "gbk"
        
        if "上证指数" in response.text:
            print(f"  ✅ 接口可用")
            return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    return False

def test_tencent():
    """测试腾讯财经"""
    print("\n【腾讯财经】")
    print("  网站: https://gu.qq.com/")
    print("  数据: 免费，无需账号")
    print("  包含: 实时行情、盘口")
    
    # 测试接口
    url = "http://qt.gtimg.cn/q=sh000001"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = "gbk"
        
        if "上证指数" in response.text:
            print(f"  ✅ 接口可用")
            return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    return False

def list_paid_sources():
    """列出付费数据源"""
    print("\n" + "="*60)
    print("💰 付费数据源（需注册）")
    print("="*60)
    
    print("\n【同花顺iFinD】")
    print("  网站: https://dict.10jqka.com.cn/")
    print("  费用: 约1000-2000元/年")
    print("  数据: 深度数据、机构研报、财务分析")
    print("  优点: 数据全面，专业级别")
    
    print("\n【东方财富Choice】")
    print("  网站: https://choice.eastmoney.com/")
    print("  费用: 约2000-3000元/年")
    print("  数据: 专业金融数据")
    print("  优点: 数据最全，机构常用")
    
    print("\n【Wind终端】")
    print("  网站: https://www.wind.com.cn/")
    print("  费用: 约5000-10000元/年")
    print("  数据: 最全的金融数据")
    print("  优点: 专业机构标配")
    
    print("\n【集思录】")
    print("  网站: https://www.jisilu.cn/")
    print("  费用: 免费注册，部分功能收费")
    print("  数据: 可转债、套利数据")
    print("  优点: 可转债数据好，免费够用")

def list_free_sources():
    """列出免费数据源"""
    print("\n" + "="*60)
    print("🆓 免费数据源（推荐）")
    print("="*60)
    
    print("\n1. 东方财富（推荐）")
    print("   - 实时行情")
    print("   - 资金流向: http://data.eastmoney.com/zjlx/")
    print("   - 龙虎榜: http://data.eastmoney.com/stock/lhb.html")
    print("   - 北向资金: http://data.eastmoney.com/hsgt/")
    print("   - 不需要账号")
    
    print("\n2. 新浪财经")
    print("   - 实时行情 + 盘口五档")
    print("   - 不需要账号")
    
    print("\n3. 同花顺")
    print("   - 行情 + 简单数据")
    print("   - 不需要账号")
    
    print("\n4. 集思录")
    print("   - 可转债数据")
    print("   - 需要注册（免费）")

def main():
    print("="*60)
    print("📊 股票数据源测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 测试免费接口
    test_eastmoney()
    test_sina()
    test_tencent()
    
    # 列出数据源
    list_free_sources()
    list_paid_sources()

if __name__ == "__main__":
    main()