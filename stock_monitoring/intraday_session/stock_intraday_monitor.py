#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 盘中监控任务
执行时间: 盘中时段 (10:00-15:00)
"""

import os
import sys
import json
import datetime
import requests
from typing import Dict, List, Any

class StockIntradayMonitor:
    def __init__(self):
        self.workspace_dir = "/root/.openclaw/workspace"
        self.results_dir = os.path.join(self.workspace_dir, "ai_agent", "results")
        self.output_dir = os.path.join(self.workspace_dir, "stock_monitoring", "intraday_session")
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 获取当前日期和时间
        self.current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.current_time = datetime.datetime.now().strftime("%H:%M")
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 加载监控配置
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """加载股票监控配置"""
        config_path = os.path.join(self.workspace_dir, "stock_monitor_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "monitoring_stocks": ["SH000001", "SZ399001", "CYBZ", "KZZ"],
                "alert_thresholds": {
                    "price_change_percent": 3.0,
                    "volume_ratio": 2.0,
                    "volatility_index": 25.0
                }
            }
    
    def get_current_market_status(self) -> Dict[str, Any]:
        """获取当前市场状态"""
        current_time = datetime.datetime.now()
        hour = current_time.hour
        minute = current_time.minute
        
        if hour == 9 and minute >= 30:
            market_phase = "opening_session"
        elif hour in [10, 11] or (hour == 9 and minute >= 30) or (hour == 11 and minute <= 30):
            market_phase = "morning_session"
        elif hour in [13, 14] or (hour == 15 and minute == 0):
            market_phase = "afternoon_session"
        else:
            market_phase = "unknown"
            
        return {
            "date": self.current_date,
            "time": self.current_time,
            "market_phase": market_phase,
            "is_active_trading": True if ((hour == 9 and minute >= 30) or hour in [10, 11, 13, 14] or (hour == 15 and minute == 0)) else False
        }
    
    def get_stock_data(self, symbol: str) -> Dict[str, Any]:
        """获取股票数据（模拟实现）"""
        # 这里应该是实际的API调用，暂时用模拟数据
        import random
        
        base_prices = {
            "SH000001": 3200.0,  # 上证指数
            "SZ399001": 10500.0, # 深证成指
            "CYBZ": 2100.0,      # 创业板指
            "KZZ": 100.0,        # 可转债指数
            "000882": 1.65,      # 华联股份
            "601866": 2.71       # 中远海发
        }
        
        base_price = base_prices.get(symbol, 10.0)
        
        # 模拟价格波动
        change_percent = random.uniform(-2.0, 2.0)
        current_price = base_price * (1 + change_percent / 100)
        
        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "volume": random.randint(1000000, 5000000),
            "turnover": round(current_price * random.randint(1000000, 5000000), 2),
            "timestamp": self.timestamp
        }
    
    def load_previous_market_data(self) -> Dict[str, Any]:
        """加载之前的市场数据"""
        # 尝试加载开盘监控数据
        market_open_dir = os.path.join(self.workspace_dir, "stock_monitoring", "market_open")
        latest_open_report = None
        
        if os.path.exists(market_open_dir):
            open_reports = [f for f in os.listdir(market_open_dir) if f.startswith("market_open_report") and f.endswith(".json")]
            if open_reports:
                open_reports.sort(reverse=True)
                latest_open_report = os.path.join(market_open_dir, open_reports[0])
        
        # 尝试加载持仓数据
        holdings_data_path = f"/root/.openclaw/workspace/ai_agent/results/stock_holdings_{self.current_date}.json"
        holdings_data = {}
        if os.path.exists(holdings_data_path):
            with open(holdings_data_path, 'r', encoding='utf-8') as f:
                holdings_data = json.load(f)
        
        return {
            "open_report": latest_open_report,
            "holdings": holdings_data.get("holdings", []),
            "watchlist": holdings_data.get("watchlist", [])
        }
    
    def analyze_market_trend(self, stock_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析市场趋势"""
        if not stock_data:
            return {"trend": "unknown", "strength": 0, "confidence": 0}
        
        # 计算平均涨跌幅
        avg_change = sum(stock["change_percent"] for stock in stock_data) / len(stock_data)
        
        if avg_change > 1.0:
            trend = "bullish"
            strength = min(100, int(avg_change * 20))
        elif avg_change < -1.0:
            trend = "bearish"
            strength = min(100, int(abs(avg_change) * 20))
        else:
            trend = "neutral"
            strength = 0
        
        # 计算置信度（基于数据量）
        confidence = min(100, len(stock_data) * 25)
        
        return {
            "trend": trend,
            "strength": strength,
            "confidence": confidence,
            "average_change": round(avg_change, 2)
        }
    
    def check_price_alerts(self, stock_data: Dict[str, Any], previous_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查价格警报"""
        alerts = []
        
        # 检查涨跌幅警报
        if abs(stock_data["change_percent"]) >= self.config["alert_thresholds"]["price_change_percent"]:
            alert = {
                "type": "PRICE_CHANGE",
                "symbol": stock_data["symbol"],
                "message": f"{stock_data['symbol']} 价格变动 {stock_data['change_percent']}%，超过阈值 {self.config['alert_thresholds']['price_change_percent']}%",
                "severity": "HIGH" if abs(stock_data["change_percent"]) > 5.0 else "MEDIUM",
                "current_value": stock_data["change_percent"]
            }
            alerts.append(alert)
        
        return alerts
    
    def generate_intraday_report(self) -> Dict[str, Any]:
        """生成盘中监控报告"""
        print(f"开始执行股票监控系统盘中监控任务 - {self.current_date} {self.current_time}")
        
        market_status = self.get_current_market_status()
        previous_data = self.load_previous_market_data()
        
        # 获取监控股票数据
        stock_data_list = []
        for symbol in self.config["monitoring_stocks"]:
            stock_data = self.get_stock_data(symbol)
            stock_data_list.append(stock_data)
        
        # 分析市场趋势
        market_trend = self.analyze_market_trend(stock_data_list)
        
        # 检查警报
        alerts = []
        for stock_data in stock_data_list:
            stock_alerts = self.check_price_alerts(stock_data, previous_data)
            alerts.extend(stock_alerts)
        
        report = {
            "timestamp": f"{self.current_date} {self.current_time}",
            "market_status": market_status,
            "market_trend": market_trend,
            "monitored_stocks": stock_data_list,
            "alerts": alerts,
            "previous_data": {
                "has_open_report": previous_data["open_report"] is not None,
                "holdings_count": len(previous_data["holdings"]),
                "watchlist_count": len(previous_data["watchlist"])
            },
            "summary": {
                "overall_market_direction": market_trend["trend"],
                "alert_count": len(alerts),
                "recommended_actions": []
            }
        }
        
        # 根据警报生成建议
        if alerts:
            for alert in alerts:
                if alert["type"] == "PRICE_CHANGE":
                    if alert["current_value"] > 0:
                        action = f"监控{alert['symbol']}获利了结机会"
                    else:
                        action = f"关注{alert['symbol']}下跌原因，考虑止损"
                    report["summary"]["recommended_actions"].append(action)
        
        return report
    
    def save_report(self, report: Dict[str, Any]):
        """保存报告"""
        # 保存详细结果
        result_file = os.path.join(self.results_dir, f"stock_intraday_{self.timestamp}.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 保存Markdown报告
        report_file = os.path.join(self.output_dir, f"intraday_report_{self.timestamp}.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 📈 股票监控系统 - 盘中监控报告\n\n")
            f.write(f"**日期**: {self.current_date}\n")
            f.write(f"**时间**: {self.current_time}\n")
            f.write(f"**市场阶段**: {report['market_status']['market_phase']}\n")
            f.write(f"**市场趋势**: {report['market_trend']['trend']} (强度: {report['market_trend']['strength']}%)\n\n")
            
            f.write("## 📊 监控股票表现\n")
            for stock in report['monitored_stocks']:
                change_emoji = "🟢" if stock['change_percent'] >= 0 else "🔴"
                f.write(f"### {stock['symbol']}\n")
                f.write(f"- **当前价格**: {stock['current_price']}\n")
                f.write(f"- **涨跌幅**: {change_emoji} {stock['change_percent']}%\n")
                f.write(f"- **成交量**: {stock['volume']:,}\n")
                f.write(f"- **成交额**: ¥{stock['turnover']:,.2f}\n\n")
            
            if report['alerts']:
                f.write("## 🚨 警报信息\n")
                for alert in report['alerts']:
                    severity_emoji = "🔴" if alert['severity'] == "HIGH" else "🟡"
                    f.write(f"{severity_emoji} **{alert['type']}**: {alert['message']}\n\n")
            
            f.write("## 📋 总结与建议\n")
            f.write(f"- **市场方向**: {report['summary']['overall_market_direction']}\n")
            f.write(f"- **警报数量**: {report['summary']['alert_count']}\n")
            
            if report['summary']['recommended_actions']:
                f.write("- **建议操作**:\n")
                for action in report['summary']['recommended_actions']:
                    f.write(f"  - {action}\n")
            else:
                f.write("- **建议操作**: 暂无特殊操作建议，持续监控\n")
        
        print(f"盘中监控报告已保存至: {report_file}")
        return result_file, report_file

def main():
    monitor = StockIntradayMonitor()
    report = monitor.generate_intraday_report()
    result_file, report_file = monitor.save_report(report)
    
    # 输出摘要
    print("\n=== 盘中监控任务完成 ===")
    print(f"日期: {report['timestamp']}")
    print(f"市场趋势: {report['market_trend']['trend']} (强度: {report['market_trend']['strength']}%)")
    print(f"监控股票: {len(report['monitored_stocks'])} 只")
    print(f"警报数量: {len(report['alerts'])} 条")
    
    if report['alerts']:
        print("\n📢 警报详情:")
        for alert in report['alerts']:
            print(f"  - {alert['message']}")

if __name__ == "__main__":
    main()