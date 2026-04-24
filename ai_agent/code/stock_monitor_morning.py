#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 盘中监控(上午)
执行时间: 工作日上午10:00左右 (A股交易时间 9:30-11:30)
"""

import json
import datetime
import requests
from typing import Dict, List, Any

def get_stock_data(stock_codes: List[str]) -> Dict[str, Any]:
    """
    获取股票实时数据
    由于无法直接访问真实的股票API，这里模拟数据获取逻辑
    """
    # 模拟股票数据
    mock_data = {
        "SH000001": {
            "name": "上证指数",
            "opening_price": 3050.25,
            "current_price": 3065.80,
            "price_change": 15.55,
            "price_change_percent": 0.51,
            "volume": 12500000000,
            "turnover": 152000000000,
            "market_sentiment": "neutral"
        },
        "SZ399001": {
            "name": "深证成指",
            "opening_price": 10200.50,
            "current_price": 10280.30,
            "price_change": 79.80,
            "price_change_percent": 0.78,
            "volume": 8900000000,
            "turnover": 98500000000,
            "market_sentiment": "positive"
        },
        "CYBZ": {
            "name": "创业板指",
            "opening_price": 2050.75,
            "current_price": 2085.40,
            "price_change": 34.65,
            "price_change_percent": 1.69,
            "volume": 3200000000,
            "turnover": 35800000000,
            "market_sentiment": "positive"
        },
        "KZZ": {
            "name": "科创50",
            "opening_price": 850.20,
            "current_price": 835.60,
            "price_change": -14.60,
            "price_change_percent": -1.72,
            "volume": 1800000000,
            "turnover": 21500000000,
            "market_sentiment": "negative"
        }
    }
    
    result = {}
    for code in stock_codes:
        if code in mock_data:
            result[code] = mock_data[code]
    
    return result

def check_alerts(stock_data: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    检查是否触发预警条件
    """
    alerts = []
    thresholds = config["alert_thresholds"]
    
    for stock_code, data in stock_data.items():
        alert_reasons = []
        
        # 检查涨跌幅预警
        if abs(data["price_change_percent"]) >= thresholds["price_change_percent"]:
            alert_reasons.append(f"涨跌幅 {data['price_change_percent']:.2f}% 超过阈值 {thresholds['price_change_percent']}%")
        
        # 这里简化处理，实际中需要历史数据来计算成交量比率和波动率
        # 模拟一些预警情况
        if stock_code == "CYBZ" and data["price_change_percent"] > 1.5:
            alert_reasons.append("创业板指涨幅较大，需关注")
        
        if alert_reasons:
            alerts.append({
                "stock_code": stock_code,
                "stock_name": data["name"],
                "current_price": data["current_price"],
                "price_change_percent": data["price_change_percent"],
                "reasons": alert_reasons,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    return alerts

def get_market_news(keywords: List[str]) -> List[Dict[str, str]]:
    """
    获取市场相关新闻（模拟）
    """
    # 模拟新闻数据
    mock_news = [
        {
            "title": "央行今日开展1000亿元逆回购操作，维护流动性合理充裕",
            "summary": "中国人民银行今日以利率招标方式开展了1000亿元7天期逆回购操作，中标利率维持不变。",
            "source": "央行官网",
            "time": "2026-04-03 09:45:00",
            "keywords": ["央行", "利率"]
        },
        {
            "title": "3月制造业PMI为51.2，连续5个月位于扩张区间",
            "summary": "国家统计局今日公布数据显示，3月份制造业采购经理指数(PMI)为51.2%，比上月上升0.5个百分点。",
            "source": "国家统计局",
            "time": "2026-04-03 09:30:00",
            "keywords": ["经济数据", "GDP"]
        }
    ]
    
    relevant_news = []
    for news in mock_news:
        if any(keyword in news["title"] or keyword in news["summary"] for keyword in keywords):
            relevant_news.append(news)
    
    return relevant_news

def generate_morning_report(stock_data: Dict[str, Any], alerts: List[Dict[str, Any]], 
                          news: List[Dict[str, str]]) -> str:
    """
    生成上午盘中监控报告
    """
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report = f"# 股票监控系统 - 盘中监控报告（上午）\n\n"
    report += f"**生成时间**: {current_time}\n\n"
    
    # 主要指数表现
    report += "## 主要指数表现\n\n"
    report += "| 指数代码 | 指数名称 | 当前价格 | 涨跌幅 | 市场情绪 |\n"
    report += "|----------|----------|----------|--------|----------|\n"
    
    for code, data in stock_data.items():
        sentiment_emoji = {"positive": "🟢", "neutral": "🟡", "negative": "🔴"}.get(data["market_sentiment"], "⚪")
        report += f"| {code} | {data['name']} | {data['current_price']:.2f} | {data['price_change_percent']:+.2f}% | {sentiment_emoji} {data['market_sentiment']} |\n"
    
    report += "\n"
    
    # 预警信息
    if alerts:
        report += "## ⚠️ 预警信息\n\n"
        for alert in alerts:
            report += f"### {alert['stock_name']} ({alert['stock_code']})\n"
            report += f"- **当前价格**: {alert['current_price']:.2f}\n"
            report += f"- **涨跌幅**: {alert['price_change_percent']:+.2f}%\n"
            report += "- **预警原因**:\n"
            for reason in alert['reasons']:
                report += f"  - {reason}\n"
            report += f"- **时间**: {alert['timestamp']}\n\n"
    else:
        report += "## ✅ 预警信息\n\n当前无触发预警的股票。\n\n"
    
    # 相关新闻
    if news:
        report += "## 📰 相关新闻\n\n"
        for n in news:
            report += f"### {n['title']}\n"
            report += f"- **来源**: {n['source']}\n"
            report += f"- **时间**: {n['time']}\n"
            report += f"- **摘要**: {n['summary']}\n\n"
    else:
        report += "## 📰 相关新闻\n\n暂无相关重要新闻。\n\n"
    
    # 操作建议
    report += "## 💡 操作建议\n\n"
    positive_count = sum(1 for data in stock_data.values() if data["market_sentiment"] == "positive")
    negative_count = sum(1 for data in stock_data.values() if data["market_sentiment"] == "negative")
    
    if positive_count > negative_count:
        report += "- 市场整体情绪偏积极，可关注强势板块机会\n"
        report += "- 创业板指表现较好，科技成长股值得关注\n"
    elif negative_count > positive_count:
        report += "- 市场整体情绪偏谨慎，建议控制仓位\n"
        report += "- 关注防御性板块和低估值蓝筹股\n"
    else:
        report += "- 市场分化明显，建议精选个股，避免追高\n"
        report += "- 密切关注下午盘面变化\n"
    
    report += "\n---\n"
    report += "*本报告基于模拟数据生成，仅供参考，不构成投资建议*"
    
    return report

def main():
    """主函数"""
    # 读取配置
    with open('/root/.openclaw/workspace/stock_monitor_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 获取股票数据
    stock_data = get_stock_data(config["monitoring_stocks"])
    
    # 检查预警
    alerts = check_alerts(stock_data, config)
    
    # 获取相关新闻
    news = get_market_news(config["news_keywords"])
    
    # 生成报告
    report = generate_morning_report(stock_data, alerts, news)
    
    # 保存报告
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    report_path = f"/root/.openclaw/workspace/ai_agent/results/stock_monitor_morning_{timestamp}.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"股票监控报告已生成: {report_path}")
    print("\n=== 报告预览 ===")
    print(report[:1000] + "..." if len(report) > 1000 else report)

if __name__ == "__main__":
    main()