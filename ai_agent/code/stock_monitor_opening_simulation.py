#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 开盘监控 (模拟数据)
由于外部API限制，使用模拟数据生成开盘监控报告
执行时间: 2026-04-06 09:30 (A股开盘时间)
"""

import json
import random
from datetime import datetime
import os

class StockMonitorOpeningSimulation:
    def __init__(self):
        self.workspace_dir = "/root/.openclaw/workspace"
        self.results_dir = os.path.join(self.workspace_dir, "ai_agent", "results")
        self.config_file = os.path.join(self.workspace_dir, "stock_monitor_config.json")
        self.monitoring_stocks = []
        self.alert_threshold = 3.0
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_status": "opening",
            "stocks_monitored": [],
            "alerts": [],
            "summary": "",
            "note": "⚠️ 注意: 由于外部数据源限制，本报告使用模拟数据生成。实际交易请以官方数据为准。"
        }
        
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            stock_symbols = config.get("monitoring_stocks", [])
            self.monitoring_stocks = []
            
            for symbol in stock_symbols:
                if symbol == "SH000001":
                    self.monitoring_stocks.append({"symbol": "000001", "name": "上证指数"})
                elif symbol == "SZ399001":
                    self.monitoring_stocks.append({"symbol": "399001", "name": "深证成指"})
                elif symbol == "CYBZ":
                    self.monitoring_stocks.append({"symbol": "399006", "name": "创业板指"})
                elif symbol == "KZZ":
                    self.monitoring_stocks.append({"symbol": "000832", "name": "可转债指数"})
                else:
                    clean_symbol = symbol.replace("SH", "").replace("SZ", "")
                    self.monitoring_stocks.append({"symbol": clean_symbol, "name": f"股票{clean_symbol}"})
            
            thresholds = config.get("alert_thresholds", {})
            self.alert_threshold = thresholds.get("price_change_percent", 3.0)
        else:
            self.monitoring_stocks = [
                {"symbol": "000001", "name": "上证指数"},
                {"symbol": "399001", "name": "深证成指"},
                {"symbol": "399006", "name": "创业板指"}
            ]
            self.alert_threshold = 3.0
            
    def generate_simulated_data(self):
        """生成模拟的股票数据"""
        # 基于历史数据生成合理的模拟值
        base_prices = {
            "000001": 3200.0,  # 上证指数
            "399001": 11500.0, # 深证成指  
            "399006": 2400.0,  # 创业板指
            "000832": 1800.0   # 可转债指数
        }
        
        for stock in self.monitoring_stocks:
            symbol = stock["symbol"]
            name = stock["name"]
            
            if symbol in base_prices:
                base_price = base_prices[symbol]
                # 生成随机涨跌幅 (-2% 到 +2%)
                change_percent = random.uniform(-2.0, 2.0)
                current_price = base_price * (1 + change_percent / 100)
                yesterday_close = base_price
                
                stock_data = {
                    "symbol": symbol,
                    "name": name,
                    "current_price": round(current_price, 2),
                    "yesterday_close": round(yesterday_close, 2),
                    "open_price": round(base_price * (1 + random.uniform(-0.5, 0.5) / 100), 2),
                    "high_price": round(current_price * (1 + random.uniform(0, 0.5) / 100), 2),
                    "low_price": round(current_price * (1 - random.uniform(0, 0.5) / 100), 2),
                    "volume": random.randint(100000000, 500000000),
                    "amount": round(random.uniform(10000000000, 50000000000), 2),
                    "change_percent": round(change_percent, 2)
                }
                
                self.results["stocks_monitored"].append(stock_data)
                
                # 检查是否触发警报（虽然模拟数据范围小，但为了演示）
                if abs(change_percent) >= self.alert_threshold:
                    alert_type = "大涨" if change_percent > 0 else "大跌"
                    self.results["alerts"].append({
                        "symbol": symbol,
                        "name": name,
                        "current_price": stock_data["current_price"],
                        "change_percent": change_percent,
                        "alert_type": alert_type,
                        "message": f"{name}({symbol}) {alert_type} {change_percent:.2f}%"
                    })
            else:
                # 其他股票使用通用模拟
                base_price = random.uniform(10, 100)
                change_percent = random.uniform(-3.0, 3.0)
                current_price = base_price * (1 + change_percent / 100)
                
                stock_data = {
                    "symbol": symbol,
                    "name": name,
                    "current_price": round(current_price, 2),
                    "yesterday_close": round(base_price, 2),
                    "change_percent": round(change_percent, 2)
                }
                self.results["stocks_monitored"].append(stock_data)
    
    def generate_summary(self):
        """生成监控摘要"""
        total_stocks = len(self.results["stocks_monitored"])
        alert_count = len(self.results["alerts"])
        
        summary_parts = []
        summary_parts.append(f"📊 股票开盘监控报告 ({self.results['timestamp']})")
        summary_parts.append(self.results["note"])
        summary_parts.append(f"📈 监控股票数量: {total_stocks}")
        summary_parts.append(f"⚠️ 警报数量: {alert_count}")
        
        if self.results["stocks_monitored"]:
            summary_parts.append("\n📋 监控详情 (模拟数据):")
            for stock in self.results["stocks_monitored"]:
                summary_parts.append(
                    f"   • {stock['name']}: {stock['current_price']:.2f} "
                    f"({stock['change_percent']:+.2f}%)"
                )
        
        if self.results["alerts"]:
            summary_parts.append("\n🚨 触发警报的股票:")
            for alert in self.results["alerts"]:
                summary_parts.append(f"   • {alert['message']}")
        
        self.results["summary"] = "\n".join(summary_parts)
    
    def save_results(self):
        """保存监控结果"""
        os.makedirs(self.results_dir, exist_ok=True)
        
        result_file = os.path.join(
            self.results_dir, 
            f"stock_monitor_opening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        latest_file = os.path.join(self.results_dir, "latest_stock_opening.json")
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
            
        summary_file = os.path.join(
            self.results_dir, 
            f"stock_summary_opening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.results["summary"])
            
        print(f"模拟结果已保存到: {result_file}")
        
    def run(self):
        """主执行方法"""
        try:
            self.load_config()
            self.generate_simulated_data()
            self.generate_summary()
            self.save_results()
            return self.results
        except Exception as e:
            error_result = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": "opening",
                "error": str(e),
                "summary": f"❌ 股票开盘监控执行失败: {str(e)}"
            }
            self.results = error_result
            self.save_results()
            raise e

if __name__ == "__main__":
    monitor = StockMonitorOpeningSimulation()
    results = monitor.run()
    print("\n" + "="*70)
    print(results["summary"])
    print("="*70)
    print("\n💡 提示: 这是模拟数据报告。如需真实数据，请配置有效的股票数据API。")