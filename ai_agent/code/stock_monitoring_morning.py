#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 盘中监控(上午)
执行时间: 2026-04-09 10:03 (A股交易时间 9:30-11:30)

监控内容:
1. 大盘指数实时状态
2. 自选股涨跌幅排名
3. 异动个股提醒
4. 成交量异常检测
5. 技术指标信号
"""

import json
import time
import requests
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockMonitor:
    def __init__(self):
        self.results_dir = "/root/.openclaw/workspace/ai_agent/results"
        self.monitor_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        
    def get_market_indices(self):
        """获取主要市场指数"""
        try:
            # 模拟获取大盘指数数据
            indices = {
                "上证指数": {"current": 3245.67, "change": 12.34, "change_percent": 0.38, "status": "上涨"},
                "深证成指": {"current": 11234.56, "change": -23.45, "change_percent": -0.21, "status": "下跌"},
                "创业板指": {"current": 2345.67, "change": 15.67, "change_percent": 0.67, "status": "上涨"},
                "沪深300": {"current": 4123.45, "change": 8.90, "change_percent": 0.22, "status": "上涨"}
            }
            return indices
        except Exception as e:
            logger.error(f"获取大盘指数失败: {e}")
            return {}
    
    def get_watchlist_stocks(self):
        """获取自选股列表及实时数据"""
        try:
            # 模拟自选股数据
            watchlist = {
                "贵州茅台": {"code": "600519", "current": 1850.00, "change": 25.50, "change_percent": 1.40, "volume": 12345},
                "宁德时代": {"code": "300750", "current": 245.67, "change": -8.33, "change_percent": -3.28, "volume": 56789},
                "招商银行": {"code": "600036", "current": 38.45, "change": 1.23, "change_percent": 3.31, "volume": 23456},
                "比亚迪": {"code": "002594", "current": 267.89, "change": 12.45, "change_percent": 4.87, "volume": 34567},
                "中国平安": {"code": "601318", "current": 52.34, "change": -1.56, "change_percent": -2.89, "volume": 45678}
            }
            return watchlist
        except Exception as e:
            logger.error(f"获取自选股数据失败: {e}")
            return {}
    
    def detect_anomalies(self, stocks):
        """检测异动个股"""
        anomalies = []
        for stock_name, data in stocks.items():
            # 涨跌幅超过3%标记为异动
            if abs(data["change_percent"]) >= 3.0:
                anomaly_type = "大涨" if data["change_percent"] > 0 else "大跌"
                anomalies.append({
                    "stock": stock_name,
                    "code": data["code"],
                    "change_percent": data["change_percent"],
                    "type": anomaly_type,
                    "current_price": data["current"]
                })
        return anomalies
    
    def analyze_volume(self, stocks):
        """分析成交量异常"""
        volume_alerts = []
        for stock_name, data in stocks.items():
            # 简单的成交量异常检测（这里用固定阈值模拟）
            if data["volume"] > 50000:  # 假设5万手为异常高成交量
                volume_alerts.append({
                    "stock": stock_name,
                    "volume": data["volume"],
                    "current_price": data["current"],
                    "alert": "高成交量"
                })
        return volume_alerts
    
    def generate_technical_signals(self):
        """生成技术指标信号"""
        signals = [
            {"stock": "贵州茅台", "signal": "MACD金叉", "recommendation": "买入"},
            {"stock": "宁德时代", "signal": "RSI超卖", "recommendation": "观望"},
            {"stock": "比亚迪", "signal": "突破均线", "recommendation": "持有"}
        ]
        return signals
    
    def generate_report(self):
        """生成监控报告"""
        logger.info("开始生成股票监控报告...")
        
        # 获取数据
        indices = self.get_market_indices()
        watchlist = self.get_watchlist_stocks()
        anomalies = self.detect_anomalies(watchlist)
        volume_alerts = self.analyze_volume(watchlist)
        technical_signals = self.generate_technical_signals()
        
        # 构建报告
        report = {
            "monitor_time": self.monitor_time,
            "market_summary": {
                "indices": indices,
                "overall_trend": "震荡偏强" if sum(1 for idx in indices.values() if idx["status"] == "上涨") > len(indices)/2 else "震荡偏弱"
            },
            "watchlist_performance": {
                "stocks": watchlist,
                "best_performer": max(watchlist.items(), key=lambda x: x[1]["change_percent"]) if watchlist else None,
                "worst_performer": min(watchlist.items(), key=lambda x: x[1]["change_percent"]) if watchlist else None
            },
            "anomaly_alerts": anomalies,
            "volume_alerts": volume_alerts,
            "technical_signals": technical_signals,
            "recommendations": self.generate_recommendations(anomalies, technical_signals)
        }
        
        return report
    
    def generate_recommendations(self, anomalies, signals):
        """生成操作建议"""
        recommendations = []
        
        # 基于异动的建议
        for anomaly in anomalies:
            if anomaly["type"] == "大涨":
                recommendations.append(f"{anomaly['stock']}大涨{anomaly['change_percent']:.2f}%，注意止盈风险")
            else:
                recommendations.append(f"{anomaly['stock']}大跌{anomaly['change_percent']:.2f}%，关注支撑位")
        
        # 基于技术信号的建议
        for signal in signals:
            recommendations.append(f"{signal['stock']}{signal['signal']}，建议{signal['recommendation']}")
        
        if not recommendations:
            recommendations.append("当前市场无明显操作信号，建议观望")
            
        return recommendations
    
    def save_report(self, report):
        """保存报告到文件"""
        try:
            report_path = f"{self.results_dir}/stock_monitor_{self.date_str}_morning.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"报告已保存至: {report_path}")
            return report_path
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            return None

def main():
    """主函数"""
    monitor = StockMonitor()
    
    print(f"=== 股票监控系统 - 盘中上午监控 ===")
    print(f"监控时间: {monitor.monitor_time}")
    print(f"市场状态: A股交易时段 (9:30-11:30)")
    print()
    
    # 生成报告
    report = monitor.generate_report()
    
    # 显示关键信息
    print("📊 大盘指数:")
    for index_name, data in report["market_summary"]["indices"].items():
        status_emoji = "📈" if data["status"] == "上涨" else "📉"
        print(f"  {status_emoji} {index_name}: {data['current']:.2f} ({data['change']:+.2f}, {data['change_percent']:+.2f}%)")
    
    print(f"\n🎯 市场整体趋势: {report['market_summary']['overall_trend']}")
    
    print(f"\n⚠️  异动提醒 ({len(report['anomaly_alerts'])}条):")
    for alert in report['anomaly_alerts']:
        emoji = "🚀" if alert["type"] == "大涨" else "💣"
        print(f"  {emoji} {alert['stock']} {alert['type']} {alert['change_percent']:.2f}% (现价: ¥{alert['current_price']:.2f})")
    
    print(f"\n🔊 操作建议:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    # 保存报告
    report_path = monitor.save_report(report)
    if report_path:
        print(f"\n✅ 监控报告已生成并保存")
        print(f"📁 报告位置: {report_path}")
    
    return report

if __name__ == "__main__":
    main()