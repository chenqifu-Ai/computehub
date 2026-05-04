#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 开盘监控
执行时间: 2026-04-06 09:30 (A股开盘时间)
"""

import json
import time
from datetime import datetime, timedelta
import requests
import os

class StockMonitorOpening:
    def __init__(self):
        self.workspace_dir = "/root/.openclaw/workspace"
        self.results_dir = os.path.join(self.workspace_dir, "ai_agent", "results")
        self.config_file = os.path.join(self.workspace_dir, "stock_monitor_config.json")
        self.monitoring_stocks = []
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_status": "opening",
            "stocks_monitored": [],
            "alerts": [],
            "summary": ""
        }
        
    def load_config(self):
        """加载监控配置"""
        default_config = {
            "stocks": [
                {"symbol": "000001", "name": "上证指数", "alert_threshold": 2.0},
                {"symbol": "399001", "name": "深证成指", "alert_threshold": 2.0},
                {"symbol": "600519", "name": "贵州茅台", "alert_threshold": 3.0},
                {"symbol": "000858", "name": "五粮液", "alert_threshold": 3.0},
                {"symbol": "601318", "name": "中国平安", "alert_threshold": 2.5}
            ],
            "market_hours": {
                "morning_start": "09:30",
                "morning_end": "11:30",
                "afternoon_start": "13:00",
                "afternoon_end": "15:00"
            },
            "data_source": "sina"
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = default_config
            # 保存默认配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
        self.monitoring_stocks = config.get("stocks", [])
        return config
    
    def get_stock_data_sina(self, symbol):
        """从新浪财经获取股票数据"""
        try:
            # 新浪财经API格式
            if symbol.startswith(('00', '30', '39')):  # 深市股票或指数
                market_prefix = "sz"
            elif symbol.startswith(('60', '000001')):  # 沪市股票或上证指数
                market_prefix = "sh"
            else:
                market_prefix = "sh"  # 默认沪市
                
            url = f"http://hq.sinajs.cn/list={market_prefix}{symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data_str = response.text.strip()
                if data_str:
                    # 解析新浪返回的数据
                    parts = data_str.split('"')[1].split(',')
                    if len(parts) > 3:
                        stock_info = {
                            "symbol": symbol,
                            "name": parts[0],
                            "current_price": float(parts[3]),
                            "yesterday_close": float(parts[2]),
                            "open_price": float(parts[1]),
                            "high_price": float(parts[4]),
                            "low_price": float(parts[5]),
                            "volume": int(parts[8]) if parts[8].isdigit() else 0,
                            "amount": float(parts[9]) if parts[9].replace('.','',1).isdigit() else 0.0
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
    
    def check_alerts(self, stock_data, alert_threshold):
        """检查是否触发警报"""
        alerts = []
        change_percent = stock_data.get("change_percent", 0)
        
        if abs(change_percent) >= alert_threshold:
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
        print("开始执行股票开盘监控...")
        config = self.load_config()
        
        # 监控每个股票
        for stock in self.monitoring_stocks:
            symbol = stock["symbol"]
            name = stock["name"]
            threshold = stock.get("alert_threshold", 2.0)
            
            print(f"监控股票: {name}({symbol})")
            stock_data = self.get_stock_data_sina(symbol)
            
            if stock_data:
                # 添加到监控结果
                self.results["stocks_monitored"].append(stock_data)
                
                # 检查警报
                alerts = self.check_alerts(stock_data, threshold)
                self.results["alerts"].extend(alerts)
                
                print(f"  当前价格: {stock_data['current_price']:.2f}")
                print(f"  涨跌幅: {stock_data['change_percent']:.2f}%")
                if alerts:
                    print(f"  ⚠️ 触发警报: {alerts[0]['message']}")
            else:
                print(f"  ❌ 获取数据失败")
                self.results["stocks_monitored"].append({
                    "symbol": symbol,
                    "name": name,
                    "error": "数据获取失败"
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
            f"stock_monitor_opening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # 保存最新结果的快捷方式
        latest_file = os.path.join(self.results_dir, "latest_stock_opening.json")
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
            
        # 保存摘要到文本文件
        summary_file = os.path.join(
            self.results_dir, 
            f"stock_summary_opening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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
    monitor = StockMonitorOpening()
    results = monitor.run()
    print("\n" + "="*50)
    print(results["summary"])
    print("="*50)