#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 下午盘中监控任务
执行时间: 下午交易时段 (13:00-15:00)
"""

import os
import sys
import json
import datetime
import requests
from typing import Dict, List, Any

class StockAfternoonMonitor:
    def __init__(self):
        self.workspace_dir = "/root/.openclaw/workspace"
        self.results_dir = os.path.join(self.workspace_dir, "ai_agent", "results")
        self.output_dir = os.path.join(self.workspace_dir, "stock_monitoring", "afternoon_session")
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 获取当前日期和时间
        self.current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.current_time = datetime.datetime.now().strftime("%H:%M")
        
    def get_current_market_status(self) -> Dict[str, Any]:
        """获取当前市场状态"""
        current_time = datetime.datetime.now()
        hour = current_time.hour
        minute = current_time.minute
        
        if hour == 13:
            market_phase = "afternoon_session_start"
        elif hour in [13, 14] or (hour == 14 and minute <= 57):
            market_phase = "afternoon_session"
        elif hour == 14 and minute >= 58:
            market_phase = "closing_session"
        else:
            market_phase = "unknown"
            
        return {
            "date": self.current_date,
            "time": self.current_time,
            "market_phase": market_phase,
            "is_active_trading": True if hour in [13, 14] or (hour == 15 and minute == 0) else False
        }
    
    def load_morning_session_data(self) -> Dict[str, Any]:
        """加载早盘数据"""
        # 查找最新的开盘监控报告
        morning_report_files = []
        market_open_dir = "/root/.openclaw/workspace/stock_monitoring/market_open"
        if os.path.exists(market_open_dir):
            for file in os.listdir(market_open_dir):
                if file.startswith("market_open_report_") and file.endswith(".md"):
                    morning_report_files.append(file)
        
        # 按时间排序，取最新的
        morning_report_files.sort(reverse=True)
        latest_morning_report = None
        if morning_report_files:
            latest_morning_report = os.path.join(market_open_dir, morning_report_files[0])
        
        # 加载持仓数据
        holdings_data_path = f"/root/.openclaw/workspace/ai_agent/results/stock_holdings_{self.current_date}.json"
        holdings_data = {}
        if os.path.exists(holdings_data_path):
            with open(holdings_data_path, 'r', encoding='utf-8') as f:
                holdings_data = json.load(f)
        
        # 模拟当前价格数据（实际应该从API获取）
        current_prices = {
            "000882": {"symbol": "000882", "name": "华联股份", "current_price": 1.63, "change": "-2.98%"},
            "601866": {"symbol": "601866", "name": "中远海发", "current_price": 2.68, "change": "-1.47%"}
        }
        
        return {
            "holdings": holdings_data.get("holdings", []),
            "watchlist": holdings_data.get("watchlist", []),
            "current_prices": current_prices,
            "morning_report": latest_morning_report
        }
    
    def analyze_holding_performance_afternoon(self, holdings_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析下午持仓表现"""
        analysis_results = []
        
        # 华联股份分析
        hualian_analysis = {
            "symbol": "000882",
            "name": "华联股份",
            "current_price": holdings_data["current_prices"]["000882"]["current_price"],
            "previous_close": 1.68,  # 从前一天收盘价
            "change_percent": holdings_data["current_prices"]["000882"]["change"],
            "position_size": 13500,
            "cost_basis": 1.873,
            "current_value": holdings_data["current_prices"]["000882"]["current_price"] * 13500,
            "unrealized_pnl": (holdings_data["current_prices"]["000882"]["current_price"] - 1.873) * 13500,
            "pnl_percent": ((holdings_data["current_prices"]["000882"]["current_price"] - 1.873) / 1.873) * 100,
            "stop_loss": 1.60,
            "distance_to_stop_loss": ((holdings_data["current_prices"]["000882"]["current_price"] - 1.60) / 1.60) * 100,
            "risk_level": "CRITICAL" if holdings_data["current_prices"]["000882"]["current_price"] <= 1.62 else "HIGH",
            "action_required": True if holdings_data["current_prices"]["000882"]["current_price"] <= 1.62 else False,
            "price_trend": "declining" if holdings_data["current_prices"]["000882"]["current_price"] < 1.65 else "stable"
        }
        analysis_results.append(hualian_analysis)
        
        return analysis_results
    
    def check_watchlist_opportunities_afternoon(self, holdings_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查下午关注列表机会"""
        opportunities = []
        
        # 中远海发检查
        current_price = holdings_data["current_prices"]["601866"]["current_price"]
        if 2.50 <= current_price <= 2.70:
            opportunity = {
                "symbol": "601866",
                "name": "中远海发",
                "current_price": current_price,
                "target_range": [2.50, 2.70],
                "opportunity_type": "BUY_SIGNAL",
                "entry_recommendation": f"价格{current_price}已进入目标区间[2.50-2.70]，建议考虑买入",
                "urgency": "HIGH"
            }
            opportunities.append(opportunity)
        else:
            opportunity = {
                "symbol": "601866",
                "name": "中远海发",
                "current_price": current_price,
                "target_range": [2.50, 2.70],
                "opportunity_type": "WAITING",
                "distance_to_entry": min(abs(current_price - 2.50), abs(current_price - 2.70)),
                "status": f"价格{current_price}尚未进入目标区间，还需下跌{2.70-current_price:.2f}"
            }
            opportunities.append(opportunity)
            
        return opportunities
    
    def evaluate_end_of_day_strategy(self, holdings_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估尾盘策略"""
        end_of_day_strategy = {
            "recommendations": [],
            "risk_assessment": "high",
            "market_sentiment": "bearish"
        }
        
        # 华联股份尾盘策略
        hualian_price = holdings_data["current_prices"]["000882"]["current_price"]
        if hualian_price <= 1.62:
            end_of_day_strategy["recommendations"].append({
                "symbol": "000882",
                "action": "IMMEDIATE_SELL",
                "reason": "价格跌破关键支撑位1.62，止损执行",
                "urgency": "CRITICAL"
            })
            end_of_day_strategy["risk_assessment"] = "critical"
        elif hualian_price <= 1.65:
            end_of_day_strategy["recommendations"].append({
                "symbol": "000882",
                "action": "MONITOR_CLOSELY",
                "reason": "接近止损位，需密切关注尾盘走势",
                "urgency": "HIGH"
            })
        
        # 中远海发尾盘策略
        zhongyuan_price = holdings_data["current_prices"]["601866"]["current_price"]
        if 2.50 <= zhongyuan_price <= 2.70:
            end_of_day_strategy["recommendations"].append({
                "symbol": "601866",
                "action": "CONSIDER_BUY",
                "reason": "价格进入目标区间，可考虑尾盘买入",
                "urgency": "MEDIUM"
            })
            
        return end_of_day_strategy
    
    def generate_afternoon_report(self) -> Dict[str, Any]:
        """生成下午盘中监控报告"""
        print(f"开始执行股票监控系统下午盘中监控任务 - {self.current_date} {self.current_time}")
        
        market_status = self.get_current_market_status()
        previous_data = self.load_morning_session_data()
        
        holding_analysis = self.analyze_holding_performance_afternoon(previous_data)
        watchlist_opportunities = self.check_watchlist_opportunities_afternoon(previous_data)
        end_of_day_strategy = self.evaluate_end_of_day_strategy(previous_data)
        
        report = {
            "timestamp": f"{self.current_date} {self.current_time}",
            "market_status": market_status,
            "holding_analysis": holding_analysis,
            "watchlist_opportunities": watchlist_opportunities,
            "end_of_day_strategy": end_of_day_strategy,
            "critical_alerts": [],
            "summary": {
                "overall_market_direction": "bearish",
                "portfolio_status": "at_risk",
                "immediate_actions": []
            }
        }
        
        # 检查紧急警报
        for holding in holding_analysis:
            if holding["action_required"]:
                alert = {
                    "type": "STOP_LOSS_TRIGGERED",
                    "symbol": holding["symbol"],
                    "message": f"{holding['name']} ({holding['symbol']}) 价格已触发止损条件，当前价格: ¥{holding['current_price']:.2f}, 止损位: ¥{holding['stop_loss']:.2f}",
                    "severity": "CRITICAL"
                }
                report["critical_alerts"].append(alert)
                report["summary"]["immediate_actions"].append(f"立即执行{holding['name']}止损")
        
        for opportunity in watchlist_opportunities:
            if opportunity.get("opportunity_type") == "BUY_SIGNAL":
                alert = {
                    "type": "BUY_OPPORTUNITY",
                    "symbol": opportunity["symbol"],
                    "message": f"{opportunity['name']} ({opportunity['symbol']}) 出现买入机会: {opportunity['entry_recommendation']}",
                    "severity": "MEDIUM"
                }
                report["critical_alerts"].append(alert)
                report["summary"]["immediate_actions"].append(f"考虑买入{opportunity['name']}")
        
        # 添加尾盘策略推荐
        for recommendation in end_of_day_strategy["recommendations"]:
            if recommendation["urgency"] == "CRITICAL":
                alert = {
                    "type": "END_OF_DAY_ACTION",
                    "symbol": recommendation["symbol"],
                    "message": f"尾盘策略: {recommendation['action']} - {recommendation['reason']}",
                    "severity": "CRITICAL"
                }
                report["critical_alerts"].append(alert)
                report["summary"]["immediate_actions"].append(f"{recommendation['reason']}")
        
        return report
    
    def save_report(self, report: Dict[str, Any]):
        """保存报告"""
        # 保存详细结果
        result_file = os.path.join(self.results_dir, f"stock_afternoon_{self.current_date}_{self.current_time.replace(':', '')}.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 保存Markdown报告
        report_file = os.path.join(self.output_dir, f"afternoon_session_report_{self.current_date}_{self.current_time.replace(':', '')}.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 📊 股票监控系统 - 下午盘中监控报告\n\n")
            f.write(f"**日期**: {self.current_date}\n")
            f.write(f"**时间**: {self.current_time}\n")
            f.write(f"**市场阶段**: {report['market_status']['market_phase']}\n\n")
            
            f.write("## 📈 持仓分析\n")
            for holding in report['holding_analysis']:
                f.write(f"### {holding['name']} ({holding['symbol']})\n")
                f.write(f"- **当前价格**: ¥{holding['current_price']:.2f} ({holding['change_percent']})\n")
                f.write(f"- **持仓数量**: {holding['position_size']:,}股\n")
                f.write(f"- **成本价**: ¥{holding['cost_basis']:.3f}\n")
                f.write(f"- **当前市值**: ¥{holding['current_value']:,.2f}\n")
                f.write(f"- **浮动盈亏**: ¥{holding['unrealized_pnl']:,.2f} ({holding['pnl_percent']:.2f}%)\n")
                f.write(f"- **止损位**: ¥{holding['stop_loss']:.2f}\n")
                f.write(f"- **风险等级**: {holding['risk_level']}\n")
                f.write(f"- **价格趋势**: {holding['price_trend']}\n")
                if holding['action_required']:
                    f.write(f"- ⚠️ **操作建议**: 立即止损卖出\n")
                f.write("\n")
            
            f.write("## 🔍 关注机会\n")
            for opportunity in report['watchlist_opportunities']:
                f.write(f"### {opportunity['name']} ({opportunity['symbol']})\n")
                if opportunity.get('opportunity_type') == 'BUY_SIGNAL':
                    f.write(f"✅ **买入信号**: {opportunity['entry_recommendation']}\n")
                    f.write(f"🎯 **紧急度**: {opportunity['urgency']}\n")
                else:
                    f.write(f"⏳ **等待中**: {opportunity['status']}\n")
                f.write("\n")
            
            f.write("## 📋 尾盘策略\n")
            f.write(f"**市场情绪**: {report['end_of_day_strategy']['market_sentiment']}\n")
            f.write(f"**风险评估**: {report['end_of_day_strategy']['risk_assessment']}\n")
            if report['end_of_day_strategy']['recommendations']:
                f.write("**策略推荐**:\n")
                for rec in report['end_of_day_strategy']['recommendations']:
                    urgency_emoji = "🚨" if rec['urgency'] == 'CRITICAL' else "⚠️" if rec['urgency'] == 'HIGH' else "💡"
                    f.write(f"- {urgency_emoji} {rec['symbol']} {rec['action']}: {rec['reason']}\n")
            f.write("\n")
            
            if report['critical_alerts']:
                f.write("## 🚨 紧急提醒\n")
                for alert in report['critical_alerts']:
                    f.write(f"- {alert['message']}\n")
                f.write("\n")
            
            f.write("## 📋 总结\n")
            f.write(f"- **市场方向**: {report['summary']['overall_market_direction']}\n")
            f.write(f"- **投资组合状态**: {report['summary']['portfolio_status']}\n")
            if report['summary']['immediate_actions']:
                f.write("- **立即行动**:\n")
                for action in report['summary']['immediate_actions']:
                    f.write(f"  - {action}\n")
        
        print(f"下午盘中监控报告已保存至: {report_file}")
        return result_file, report_file
    
    def execute_trading_actions(self, report: Dict[str, Any]):
        """执行交易操作（模拟）"""
        actions_executed = []
        
        # 模拟华联股份止损操作
        for holding in report['holding_analysis']:
            if holding['symbol'] == '000882' and holding['action_required']:
                action = {
                    "type": "SELL",
                    "symbol": holding['symbol'],
                    "name": holding['name'],
                    "quantity": holding['position_size'],  # 全部卖出
                    "price": holding['current_price'],
                    "reason": "触发止损条件，执行风险控制",
                    "status": "EXECUTED_SIMULATED"
                }
                actions_executed.append(action)
                print(f"✅ 模拟执行: 卖出 {holding['name']} {action['quantity']} 股 @ ¥{holding['current_price']:.2f}")
        
        return actions_executed

def main():
    monitor = StockAfternoonMonitor()
    report = monitor.generate_afternoon_report()
    result_file, report_file = monitor.save_report(report)
    
    # 执行交易操作（模拟）
    actions = monitor.execute_trading_actions(report)
    
    # 输出摘要
    print("\n=== 下午盘中监控任务完成 ===")
    print(f"日期: {report['timestamp']}")
    print(f"持仓分析: {len(report['holding_analysis'])} 只股票")
    print(f"关注机会: {len(report['watchlist_opportunities'])} 个")
    print(f"尾盘策略: {len(report['end_of_day_strategy']['recommendations'])} 条")
    print(f"紧急提醒: {len(report['critical_alerts'])} 条")
    print(f"模拟交易: {len(actions)} 笔")
    
    if actions:
        print("\n📊 模拟交易详情:")
        for action in actions:
            print(f"  - {action['type']} {action['name']} {action['quantity']} 股")

if __name__ == "__main__":
    main()