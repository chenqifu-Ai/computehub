#!/usr/bin/env python3
"""
股票监控系统 - 开盘监控
监控A股市场开盘情况，获取主要指数和个股数据
"""

import requests
import json
import datetime
from typing import Dict, List

def get_market_indices() -> Dict:
    """
    获取主要市场指数数据
    由于无法直接访问实时金融API，这里模拟获取主要指数数据
    """
    # 模拟数据 - 实际应用中应替换为真实的API调用
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    indices = {
        "上证指数": {
            "code": "000001.SH",
            "current": 3050.25,
            "change": 15.32,
            "change_percent": 0.51,
            "time": current_time
        },
        "深证成指": {
            "code": "399001.SZ",
            "current": 11200.78,
            "change": -23.45,
            "change_percent": -0.21,
            "time": current_time
        },
        "创业板指": {
            "code": "399006.SZ",
            "current": 2280.15,
            "change": 8.76,
            "change_percent": 0.39,
            "time": current_time
        }
    }
    return indices

def get_watchlist_stocks() -> List[Dict]:
    """
    获取自选股监控列表
    """
    # 模拟自选股数据
    watchlist = [
        {
            "name": "贵州茅台",
            "code": "600519.SH",
            "current": 1850.50,
            "change": 25.30,
            "change_percent": 1.39,
            "volume": 1250000
        },
        {
            "name": "宁德时代",
            "code": "300750.SZ",
            "current": 195.80,
            "change": -3.20,
            "change_percent": -1.61,
            "volume": 3500000
        },
        {
            "name": "中国平安",
            "code": "601318.SH",
            "current": 48.75,
            "change": 0.85,
            "change_percent": 1.77,
            "volume": 2800000
        }
    ]
    return watchlist

def analyze_market_status(indices: Dict) -> str:
    """
    分析市场整体状态
    """
    sh_change = indices["上证指数"]["change_percent"]
    sz_change = indices["深证成指"]["change_percent"]
    cyb_change = indices["创业板指"]["change_percent"]
    
    if sh_change > 0 and sz_change > 0 and cyb_change > 0:
        status = "📈 市场整体上涨"
    elif sh_change < 0 and sz_change < 0 and cyb_change < 0:
        status = "📉 市场整体下跌"
    else:
        status = "📊 市场分化明显"
    
    return status

def generate_market_report():
    """
    生成市场监控报告
    """
    print("=== 股票监控系统 - 开盘监控报告 ===")
    print(f"监控时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取市场指数
    indices = get_market_indices()
    print("【主要市场指数】")
    for name, data in indices.items():
        direction = "↑" if data["change"] >= 0 else "↓"
        change_sign = "+" if data["change"] >= 0 else ""
        print(f"{name} ({data['code']}): {data['current']:.2f} {direction} {change_sign}{data['change']:.2f} ({change_sign}{data['change_percent']:.2f}%)")
    print()
    
    # 分析市场状态
    market_status = analyze_market_status(indices)
    print(f"【市场整体状态】{market_status}")
    print()
    
    # 获取自选股
    watchlist = get_watchlist_stocks()
    print("【自选股监控】")
    for stock in watchlist:
        direction = "↑" if stock["change"] >= 0 else "↓"
        change_sign = "+" if stock["change"] >= 0 else ""
        print(f"{stock['name']} ({stock['code']}): {stock['current']:.2f} {direction} {change_sign}{stock['change']:.2f} ({change_sign}{stock['change_percent']:.2f}%) | 成交量: {stock['volume']:,}")
    print()
    
    # 风险提示
    print("【风险提示】")
    print("• 本监控数据为模拟数据，仅供参考")
    print("• 实际投资请以交易所官方数据为准")
    print("• 市场有风险，投资需谨慎")
    
    return {
        "indices": indices,
        "watchlist": watchlist,
        "market_status": market_status,
        "timestamp": datetime.datetime.now().isoformat()
    }

if __name__ == "__main__":
    report_data = generate_market_report()
    
    # 保存报告数据到文件
    with open("/root/.openclaw/workspace/ai_agent/results/stock_monitor_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 监控报告已生成并保存")