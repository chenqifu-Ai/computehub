#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 集合竞价分析任务
执行时间: 集合竞价期间 (9:15-9:25) 和开盘前 (9:25-9:30)
"""

import os
import sys
import json
import datetime
import requests
from typing import Dict, List, Any

class CollectionBiddingAnalyzer:
    def __init__(self):
        self.workspace_dir = "/root/.openclaw/workspace"
        self.results_dir = os.path.join(self.workspace_dir, "ai_agent", "results")
        self.output_dir = os.path.join(self.workspace_dir, "stock_monitoring", "market_open")
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 获取当前日期和时间
        self.current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.current_hour = datetime.datetime.now().hour
        self.current_minute = datetime.datetime.now().minute
        
    def get_collection_bidding_status(self) -> Dict[str, Any]:
        """获取集合竞价状态"""
        current_time = datetime.datetime.now()
        hour = current_time.hour
        minute = current_time.minute
        
        if hour == 9 and 15 <= minute < 20:
            bidding_phase = "initial_bidding"
        elif hour == 9 and 20 <= minute < 25:
            bidding_phase = "continuous_bidding"
        elif hour == 9 and 25 <= minute < 30:
            bidding_phase = "pre_opening"
        else:
            bidding_phase = "unknown"
            
        return {
            "date": self.current_date,
            "time": self.current_time,
            "bidding_phase": bidding_phase,
            "is_collection_bidding_active": True if (hour == 9 and 15 <= minute < 30) else False,
            "minutes_to_opening": max(0, 30 - minute) if hour == 9 else None
        }
    
    def load_stock_config(self) -> Dict[str, Any]:
        """加载股票监控配置"""
        config_path = "/root/.openclaw/workspace/stock_monitor_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 默认配置
            return {
                "monitoring_stocks": ["SH000001", "SZ399001", "000882", "601866"],
                "alert_thresholds": {
                    "price_change_percent": 3.0,
                    "volume_ratio": 2.0
                }
            }
    
    def simulate_collection_bidding_data(self) -> Dict[str, Any]:
        """模拟集合竞价数据（实际应从API获取）"""
        # 基于配置中的股票列表生成模拟数据
        config = self.load_stock_config()
        monitoring_stocks = config.get("monitoring_stocks", [])
        
        # 添加我们关注的具体股票
        if "000882" not in monitoring_stocks:
            monitoring_stocks.extend(["000882", "601866"])
        
        bidding_data = {}
        
        for stock in monitoring_stocks:
            if stock == "000882":  # 华联股份
                # 模拟华联股份集合竞价数据
                previous_close = 1.68
                # 根据当前时间调整价格（越接近9:25，价格越确定）
                if self.current_minute >= 25:
                    # 开盘前最后价格
                    simulated_price = 1.65
                    volume_ratio = 1.8
                elif self.current_minute >= 20:
                    # 连续竞价阶段
                    simulated_price = round(1.64 + (1.65 - 1.64) * (self.current_minute - 20) / 5, 2)
                    volume_ratio = 1.5 + (1.8 - 1.5) * (self.current_minute - 20) / 5
                else:
                    # 初始竞价阶段
                    simulated_price = round(1.62 + (1.64 - 1.62) * self.current_minute / 20, 2)
                    volume_ratio = 1.2 + (1.5 - 1.2) * self.current_minute / 20
                
                price_change = simulated_price - previous_close
                price_change_percent = (price_change / previous_close) * 100
                
                bidding_data[stock] = {
                    "symbol": stock,
                    "name": "华联股份",
                    "previous_close": previous_close,
                    "collection_bidding_price": simulated_price,
                    "price_change": round(price_change, 2),
                    "price_change_percent": round(price_change_percent, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "bid_volume": 15000000,
                    "ask_volume": 12000000,
                    "net_flow": 3000000,
                    "sentiment": "bearish" if price_change_percent < 0 else "bullish"
                }
                
            elif stock == "601866":  # 中远海发
                previous_close = 2.72
                if self.current_minute >= 25:
                    simulated_price = 2.71
                    volume_ratio = 1.3
                elif self.current_minute >= 20:
                    simulated_price = round(2.70 + (2.71 - 2.70) * (self.current_minute - 20) / 5, 2)
                    volume_ratio = 1.1 + (1.3 - 1.1) * (self.current_minute - 20) / 5
                else:
                    simulated_price = round(2.68 + (2.70 - 2.68) * self.current_minute / 20, 2)
                    volume_ratio = 0.9 + (1.1 - 0.9) * self.current_minute / 20
                
                price_change = simulated_price - previous_close
                price_change_percent = (price_change / previous_close) * 100
                
                bidding_data[stock] = {
                    "symbol": stock,
                    "name": "中远海发",
                    "previous_close": previous_close,
                    "collection_bidding_price": simulated_price,
                    "price_change": round(price_change, 2),
                    "price_change_percent": round(price_change_percent, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "bid_volume": 8000000,
                    "ask_volume": 7500000,
                    "net_flow": 500000,
                    "sentiment": "bearish" if price_change_percent < 0 else "bullish"
                }
                
            elif stock in ["SH000001", "SZ399001"]:
                # 大盘指数
                index_name = "上证指数" if stock == "SH000001" else "深证成指"
                previous_close = 3050 if stock == "SH000001" else 9850
                
                if self.current_minute >= 25:
                    simulated_price = 3042 if stock == "SH000001" else 9820
                elif self.current_minute >= 20:
                    base_price = 3035 if stock == "SH000001" else 9810
                    target_price = 3042 if stock == "SH000001" else 9820
                    simulated_price = round(base_price + (target_price - base_price) * (self.current_minute - 20) / 5, 2)
                else:
                    base_price = 3030 if stock == "SH000001" else 9800
                    target_price = 3035 if stock == "SH000001" else 9810
                    simulated_price = round(base_price + (target_price - base_price) * self.current_minute / 20, 2)
                
                price_change = simulated_price - previous_close
                price_change_percent = (price_change / previous_close) * 100
                
                bidding_data[stock] = {
                    "symbol": stock,
                    "name": index_name,
                    "previous_close": previous_close,
                    "collection_bidding_price": simulated_price,
                    "price_change": round(price_change, 2),
                    "price_change_percent": round(price_change_percent, 2),
                    "sentiment": "bearish" if price_change_percent < 0 else "bullish"
                }
        
        return bidding_data
    
    def analyze_bidding_patterns(self, bidding_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析集合竞价模式"""
        config = self.load_stock_config()
        alert_thresholds = config.get("alert_thresholds", {})
        price_change_threshold = alert_thresholds.get("price_change_percent", 3.0)
        volume_ratio_threshold = alert_thresholds.get("volume_ratio", 2.0)
        
        analysis_results = {
            "market_overview": {},
            "individual_analysis": {},
            "alerts": [],
            "recommendations": []
        }
        
        # 分析大盘
        market_sentiment = "neutral"
        if "SH000001" in bidding_data:
            sh_index = bidding_data["SH000001"]
            if sh_index["price_change_percent"] < -0.5:
                market_sentiment = "bearish"
            elif sh_index["price_change_percent"] > 0.5:
                market_sentiment = "bullish"
        
        analysis_results["market_overview"] = {
            "sentiment": market_sentiment,
            "shanghai_index": bidding_data.get("SH000001", {}),
            "shenzhen_index": bidding_data.get("SZ399001", {})
        }
        
        # 分析个股
        for symbol, data in bidding_data.items():
            if symbol in ["SH000001", "SZ399001"]:
                continue
                
            individual_analysis = {
                "symbol": symbol,
                "name": data["name"],
                "risk_level": "normal",
                "action_required": False,
                "key_observations": []
            }
            
            # 检查价格变动警报
            if abs(data["price_change_percent"]) >= price_change_threshold:
                alert_msg = f"{data['name']} ({symbol}) 集合竞价价格变动 {data['price_change_percent']:.2f}%，超过阈值 {price_change_threshold}%"
                analysis_results["alerts"].append({
                    "type": "PRICE_MOVEMENT",
                    "severity": "HIGH" if abs(data["price_change_percent"]) >= price_change_threshold * 1.5 else "MEDIUM",
                    "message": alert_msg,
                    "symbol": symbol
                })
                individual_analysis["risk_level"] = "high"
                individual_analysis["action_required"] = True
                individual_analysis["key_observations"].append(f"价格大幅波动: {data['price_change_percent']:.2f}%")
            
            # 检查成交量警报
            if "volume_ratio" in data and data["volume_ratio"] >= volume_ratio_threshold:
                alert_msg = f"{data['name']} ({symbol}) 集合竞价成交量比 {data['volume_ratio']:.2f}，超过阈值 {volume_ratio_threshold}"
                analysis_results["alerts"].append({
                    "type": "VOLUME_SPIKE",
                    "severity": "MEDIUM",
                    "message": alert_msg,
                    "symbol": symbol
                })
                individual_analysis["key_observations"].append(f"成交量放大: {data['volume_ratio']:.2f}倍")
            
            # 特殊分析：华联股份
            if symbol == "000882":
                if data["collection_bidding_price"] <= 1.62:
                    alert_msg = f"华联股份 ({symbol}) 集合竞价价格 ¥{data['collection_bidding_price']:.2f} 接近止损位 ¥1.60"
                    analysis_results["alerts"].append({
                        "type": "STOP_LOSS_NEAR",
                        "severity": "CRITICAL",
                        "message": alert_msg,
                        "symbol": symbol
                    })
                    individual_analysis["risk_level"] = "critical"
                    individual_analysis["action_required"] = True
                    individual_analysis["key_observations"].append("价格接近止损位")
                    
                    # 生成操作建议
                    analysis_results["recommendations"].append({
                        "symbol": symbol,
                        "name": data["name"],
                        "action": "CONSIDER_SELLING",
                        "reason": "集合竞价价格接近止损位，建议开盘后密切关注并准备减仓",
                        "urgency": "HIGH"
                    })
            
            # 特殊分析：中远海发
            if symbol == "601866":
                if 2.50 <= data["collection_bidding_price"] <= 2.70:
                    analysis_results["recommendations"].append({
                        "symbol": symbol,
                        "name": data["name"],
                        "action": "MONITOR_FOR_BUY",
                        "reason": f"集合竞价价格 ¥{data['collection_bidding_price']:.2f} 进入目标买入区间 [2.50-2.70]",
                        "urgency": "MEDIUM"
                    })
                    individual_analysis["key_observations"].append("价格进入买入区间")
            
            analysis_results["individual_analysis"][symbol] = individual_analysis
        
        return analysis_results
    
    def generate_collection_bidding_report(self) -> Dict[str, Any]:
        """生成集合竞价分析报告"""
        print(f"开始执行股票监控系统集合竞价分析任务 - {self.current_date} {self.current_time}")
        
        bidding_status = self.get_collection_bidding_status()
        bidding_data = self.simulate_collection_bidding_data()
        analysis_results = self.analyze_bidding_patterns(bidding_data)
        
        report = {
            "timestamp": f"{self.current_date} {self.current_time}",
            "bidding_status": bidding_status,
            "bidding_data": bidding_data,
            "analysis_results": analysis_results,
            "summary": {
                "overall_market_direction": analysis_results["market_overview"]["sentiment"],
                "portfolio_risk_level": "normal",
                "immediate_actions_needed": len([a for a in analysis_results["alerts"] if a["severity"] in ["HIGH", "CRITICAL"]]),
                "key_recommendations": len(analysis_results["recommendations"])
            }
        }
        
        # 确定整体风险等级
        critical_alerts = [a for a in analysis_results["alerts"] if a["severity"] == "CRITICAL"]
        high_alerts = [a for a in analysis_results["alerts"] if a["severity"] == "HIGH"]
        
        if critical_alerts:
            report["summary"]["portfolio_risk_level"] = "critical"
        elif high_alerts:
            report["summary"]["portfolio_risk_level"] = "high"
        elif analysis_results["alerts"]:
            report["summary"]["portfolio_risk_level"] = "medium"
        
        return report
    
    def save_report(self, report: Dict[str, Any]):
        """保存报告"""
        # 保存详细结果
        result_file = os.path.join(self.results_dir, f"collection_bidding_{self.current_date}_{self.current_time.replace(':', '')}.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 保存Markdown报告
        report_file = os.path.join(self.output_dir, f"collection_bidding_report_{self.current_date}_{self.current_time.replace(':', '')}.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 📊 股票监控系统 - 集合竞价分析报告\n\n")
            f.write(f"**日期**: {self.current_date}\n")
            f.write(f"**时间**: {self.current_time}\n")
            f.write(f"**集合竞价阶段**: {report['bidding_status']['bidding_phase']}\n")
            f.write(f"**距离开盘**: {report['bidding_status']['minutes_to_opening']} 分钟\n\n")
            
            # 大盘情况
            f.write("## 📈 大盘指数\n")
            if "SH000001" in report['bidding_data']:
                sh_data = report['bidding_data']['SH000001']
                f.write(f"### 上证指数\n")
                f.write(f"- **集合竞价价格**: {sh_data['collection_bidding_price']:.2f}\n")
                f.write(f"- **涨跌幅**: {sh_data['price_change']:+.2f} ({sh_data['price_change_percent']:+.2f}%)\n")
                f.write(f"- **市场情绪**: {sh_data['sentiment']}\n\n")
            
            if "SZ399001" in report['bidding_data']:
                sz_data = report['bidding_data']['SZ399001']
                f.write(f"### 深证成指\n")
                f.write(f"- **集合竞价价格**: {sz_data['collection_bidding_price']:.2f}\n")
                f.write(f"- **涨跌幅**: {sz_data['price_change']:+.2f} ({sz_data['price_change_percent']:+.2f}%)\n")
                f.write(f"- **市场情绪**: {sz_data['sentiment']}\n\n")
            
            # 个股分析
            f.write("## 📊 重点关注股票\n")
            for symbol, data in report['bidding_data'].items():
                if symbol in ["SH000001", "SZ399001"]:
                    continue
                
                f.write(f"### {data['name']} ({symbol})\n")
                f.write(f"- **集合竞价价格**: ¥{data['collection_bidding_price']:.2f}\n")
                f.write(f"- **昨收价**: ¥{data['previous_close']:.2f}\n")
                f.write(f"- **涨跌幅**: {data['price_change']:+.2f} ({data['price_change_percent']:+.2f}%)\n")
                
                if "volume_ratio" in data:
                    f.write(f"- **成交量比**: {data['volume_ratio']:.2f}x\n")
                
                if "net_flow" in data:
                    f.write(f"- **净流入**: {'+' if data['net_flow'] > 0 else ''}{data['net_flow']:,}\n")
                
                f.write(f"- **情绪**: {data['sentiment']}\n")
                
                # 显示分析结果
                if symbol in report['analysis_results']['individual_analysis']:
                    analysis = report['analysis_results']['individual_analysis'][symbol]
                    f.write(f"- **风险等级**: {analysis['risk_level'].upper()}\n")
                    if analysis['key_observations']:
                        f.write(f"- **关键观察**: {', '.join(analysis['key_observations'])}\n")
                
                f.write("\n")
            
            # 警报
            if report['analysis_results']['alerts']:
                f.write("## 🚨 警报信息\n")
                for alert in report['analysis_results']['alerts']:
                    severity_emoji = "🔴" if alert['severity'] == "CRITICAL" else "🟠" if alert['severity'] == "HIGH" else "🟡"
                    f.write(f"{severity_emoji} **{alert['severity']}** - {alert['message']}\n")
                f.write("\n")
            
            # 操作建议
            if report['analysis_results']['recommendations']:
                f.write("## 💡 操作建议\n")
                for rec in report['analysis_results']['recommendations']:
                    urgency_emoji = "❗" if rec['urgency'] == "HIGH" else "⚠️" if rec['urgency'] == "MEDIUM" else "ℹ️"
                    f.write(f"{urgency_emoji} **{rec['name']} ({rec['symbol']})**\n")
                    f.write(f"   - **建议**: {rec['action']}\n")
                    f.write(f"   - **理由**: {rec['reason']}\n")
                f.write("\n")
            
            # 总结
            f.write("## 📋 总结\n")
            f.write(f"- **市场方向**: {report['summary']['overall_market_direction']}\n")
            f.write(f"- **投资组合风险**: {report['summary']['portfolio_risk_level'].upper()}\n")
            f.write(f"- **紧急操作**: {report['summary']['immediate_actions_needed']} 项\n")
            f.write(f"- **建议机会**: {report['summary']['key_recommendations']} 个\n")
        
        print(f"集合竞价分析报告已保存至: {report_file}")
        return result_file, report_file
    
    def execute(self):
        """执行集合竞价分析"""
        try:
            report = self.generate_collection_bidding_report()
            result_file, report_file = self.save_report(report)
            
            # 输出摘要
            print("\n=== 集合竞价分析任务完成 ===")
            print(f"时间: {report['timestamp']}")
            print(f"阶段: {report['bidding_status']['bidding_phase']}")
            print(f"大盘情绪: {report['analysis_results']['market_overview']['sentiment']}")
            print(f"警报数量: {len(report['analysis_results']['alerts'])}")
            print(f"操作建议: {len(report['analysis_results']['recommendations'])}")
            
            # 如果有高危警报，特别提醒
            critical_alerts = [a for a in report['analysis_results']['alerts'] if a['severity'] == 'CRITICAL']
            if critical_alerts:
                print(f"\n🚨 发现 {len(critical_alerts)} 个紧急警报!")
                for alert in critical_alerts:
                    print(f"   - {alert['message']}")
            
            return report
            
        except Exception as e:
            print(f"❌ 集合竞价分析执行失败: {str(e)}")
            raise

def main():
    analyzer = CollectionBiddingAnalyzer()
    analyzer.execute()

if __name__ == "__main__":
    main()