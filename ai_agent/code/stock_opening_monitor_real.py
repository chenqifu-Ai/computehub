#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票开盘监控系统 - 使用腾讯财经真实数据
执行时间: 开盘时段 (9:30-11:30)
"""

import json
import time
from datetime import datetime
import requests
import os

class StockOpeningMonitor:
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
            "summary": ""
        }
        
    def load_config(self):
        """加载监控配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            stock_symbols = config.get("monitoring_stocks", [])
            self.monitoring_stocks = []
            
            for symbol in stock_symbols:
                if symbol == "SH000001":
                    self.monitoring_stocks.append({"symbol": "sh000001", "name": "上证指数", "type": "index"})
                elif symbol == "SZ399001":
                    self.monitoring_stocks.append({"symbol": "sz399001", "name": "深证成指", "type": "index"})
                elif symbol == "CYBZ":
                    self.monitoring_stocks.append({"symbol": "sz399006", "name": "创业板指", "type": "index"})
                elif symbol == "KZZ":
                    self.monitoring_stocks.append({"symbol": "sh000832", "name": "可转债指数", "type": "index"})
                else:
                    # 处理其他股票代码
                    clean_symbol = symbol.replace("SH", "").replace("SZ", "")
                    market_prefix = "sh" if symbol.startswith("SH") else "sz"
                    self.monitoring_stocks.append({
                        "symbol": f"{market_prefix}{clean_symbol}", 
                        "name": f"股票{clean_symbol}",
                        "type": "stock"
                    })
            
            thresholds = config.get("alert_thresholds", {})
            self.alert_threshold = thresholds.get("price_change_percent", 3.0)
            
        else:
            # 默认配置
            self.monitoring_stocks = [
                {"symbol": "sh000001", "name": "上证指数", "type": "index"},
                {"symbol": "sz399001", "name": "深证成指", "type": "index"},
                {"symbol": "sz399006", "name": "创业板指", "type": "index"}
            ]
            self.alert_threshold = 3.0
            
        return self.monitoring_stocks
    
    def get_stock_data_tencent(self, symbol):
        """从腾讯财经获取股票数据"""
        try:
            url = f"http://qt.gtimg.cn/q={symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data_str = response.text.strip()
                if data_str and len(data_str) > 20:
                    # 解析腾讯财经返回的数据
                    # 格式: v_sh000001="51~上证指数~000001~当前价~昨收~今开~..."
                    if '="' in data_str:
                        content = data_str.split('="')[1].rstrip('"')
                        parts = content.split('~')
                        
                        if len(parts) >= 6:
                            stock_info = {
                                "symbol": symbol,
                                "name": parts[1],
                                "current_price": float(parts[3]) if parts[3] else 0.0,
                                "yesterday_close": float(parts[4]) if parts[4] else 0.0,
                                "open_price": float(parts[5]) if parts[5] else 0.0,
                                "high_price": float(parts[33]) if len(parts) > 33 and parts[33] else 0.0,
                                "low_price": float(parts[34]) if len(parts) > 34 and parts[34] else 0.0,
                                "volume": int(parts[6]) if parts[6].isdigit() else 0
                            }
                            
                            # 计算涨跌幅
                            if stock_info["yesterday_close"] > 0:
                                stock_info["change_percent"] = (
                                    (stock_info["current_price"] - stock_info["yesterday_close"]) / 
                                    stock_info["yesterday_close"] * 100
                                )
                            else:
                                stock_info["change_percent"] = 0.0
                                
                            return stock_info
        except Exception as e:
            print(f"获取股票 {symbol} 数据失败: {e}")
            
        return None
    
    def check_alerts(self, stock_data):
        """检查是否触发警报"""
        alerts = []
        change_percent = stock_data.get("change_percent", 0)
        
        if abs(change_percent) >= self.alert_threshold:
            alert_type = "大涨" if change_percent > 0 else "大跌"
            alerts.append({
                "symbol": stock_data["symbol"],
                "name": stock_data["name"],
                "current_price": stock_data["current_price"],
                "change_percent": change_percent,
                "alert_type": alert_type,
                "message": f"{stock_data['name']}({stock_data['symbol']}) {alert_type} {change_percent:.2f}%"
            })
            
        return alerts
    
    def monitor_opening(self):
        """执行开盘监控"""
        print("开始执行股票开盘监控（使用腾讯财经真实数据）...")
        self.load_config()
        
        print(f"监控股票列表: {[stock['name'] for stock in self.monitoring_stocks]}")
        print(f"警报阈值: {self.alert_threshold}%")
        
        # 监控每个股票
        for stock in self.monitoring_stocks:
            symbol = stock["symbol"]
            name = stock["name"]
            
            print(f"监控股票: {name}({symbol})")
            stock_data = self.get_stock_data_tencent(symbol)
            
            if stock_data:
                # 添加到监控结果
                self.results["stocks_monitored"].append(stock_data)
                
                # 检查警报
                alerts = self.check_alerts(stock_data)
                self.results["alerts"].extend(alerts)
                
                print(f"  当前价格: {stock_data['current_price']:.2f}")
                print(f"  昨日收盘: {stock_data['yesterday_close']:.2f}")
                print(f"  今日开盘: {stock_data['open_price']:.2f}")
                print(f"  涨跌幅: {stock_data['change_percent']:.2f}%")
                if alerts:
                    print(f"  ⚠️ 触发警报: {alerts[0]['message']}")
            else:
                print(f"  ❌ 获取数据失败或无数据")
                self.results["stocks_monitored"].append({
                    "symbol": symbol,
                    "name": name,
                    "error": "数据获取失败或无数据"
                })
                
            # 避免请求过于频繁
            time.sleep(0.5)
        
        # 生成摘要
        self.generate_summary()
        
    def generate_summary(self):
        """生成监控摘要"""
        total_stocks = len(self.results["stocks_monitored"])
        successful_stocks = len([s for s in self.results["stocks_monitored"] if "error" not in s])
        alert_count = len(self.results["alerts"])
        
        summary_parts = []
        summary_parts.append(f"📊 股票开盘监控报告 ({self.results['timestamp']})")
        summary_parts.append(f"📈 监控股票数量: {total_stocks} ({successful_stocks} 成功)")
        summary_parts.append(f"⚠️ 警报数量: {alert_count}")
        
        if self.results["stocks_monitored"]:
            summary_parts.append("\n📋 监控详情:")
            for stock in self.results["stocks_monitored"]:
                if "error" not in stock:
                    summary_parts.append(
                        f"   • {stock['name']}: {stock['current_price']:.2f} "
                        f"(开盘:{stock['open_price']:.2f}, 涨跌:{stock['change_percent']:+.2f}%)"
                    )
                else:
                    summary_parts.append(f"   • {stock['name']}: ❌ {stock['error']}")
        
        if self.results["alerts"]:
            summary_parts.append("\n🚨 触发警报的股票:")
            for alert in self.results["alerts"]:
                summary_parts.append(f"   • {alert['message']}")
        
        self.results["summary"] = "\n".join(summary_parts)
    
    def save_results(self):
        """保存监控结果"""
        # 确保结果目录存在
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 保存详细结果
        result_file = os.path.join(
            self.results_dir, 
            f"stock_opening_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # 保存最新结果的快捷方式
        latest_file = os.path.join(self.results_dir, "latest_stock_opening_real.json")
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
            
        # 保存摘要到文本文件
        summary_file = os.path.join(
            self.results_dir, 
            f"stock_summary_opening_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.results["summary"])
            
        print(f"结果已保存到: {result_file}")
        print(f"摘要已保存到: {summary_file}")
        
    def run(self):
        """主执行方法"""
        try:
            self.monitor_opening()
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
    monitor = StockOpeningMonitor()
    results = monitor.run()
    print("\n" + "="*60)
    print(results["summary"])
    print("="*60)