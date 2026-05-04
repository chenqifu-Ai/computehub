#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控系统 - 盘前任务
执行时间: 交易日早上8:20 (北京时间)
功能: 收集盘前数据、分析市场情绪、准备交易策略
"""

import os
import json
import datetime
import requests
from typing import Dict, List, Any

class StockMonitorPreMarket:
    def __init__(self):
        self.workspace_dir = "/root/.openclaw/workspace"
        self.code_dir = os.path.join(self.workspace_dir, "ai_agent", "code")
        self.results_dir = os.path.join(self.workspace_dir, "ai_agent", "results")
        self.config_file = os.path.join(self.workspace_dir, "stock_config.json")
        
        # 确保目录存在
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 加载配置
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """加载股票监控配置"""
        default_config = {
            "watchlist": ["AAPL", "MSFT", "GOOGL", "TSLA", "BABA", "000001.SS", "600036.SS"],
            "market_hours": {
                "shanghai": {"open": "09:30", "close": "15:00"},
                "nasdaq": {"open": "21:30", "close": "04:00"}  # 北京时间
            },
            "data_sources": {
                "alpha_vantage": "",
                "yfinance": True,
                "local_simulation": True
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return default_config
        else:
            # 创建默认配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def get_current_datetime_info(self) -> Dict[str, Any]:
        """获取当前日期时间信息"""
        now = datetime.datetime.now()
        beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
        now_beijing = now.replace(tzinfo=beijing_tz)
        
        return {
            "datetime": now_beijing.isoformat(),
            "date": now_beijing.strftime("%Y-%m-%d"),
            "time": now_beijing.strftime("%H:%M:%S"),
            "weekday": now_beijing.weekday(),  # 0=Monday, 6=Sunday
            "is_trading_day": now_beijing.weekday() < 5  # 周一到周五
        }
    
    def simulate_pre_market_data(self) -> Dict[str, Any]:
        """模拟盘前数据（实际应用中会调用真实API）"""
        watchlist = self.config["watchlist"]
        pre_market_data = {}
        
        # 模拟一些基础数据
        base_prices = {
            "AAPL": 175.50,
            "MSFT": 405.20,
            "GOOGL": 150.80,
            "TSLA": 175.30,
            "BABA": 75.40,
            "000001.SS": 3200.50,
            "600036.SS": 35.20
        }
        
        for symbol in watchlist:
            base_price = base_prices.get(symbol, 100.0)
            # 模拟盘前价格变动 (-2% 到 +2%)
            import random
            change_pct = random.uniform(-2.0, 2.0)
            pre_market_price = base_price * (1 + change_pct / 100)
            
            pre_market_data[symbol] = {
                "symbol": symbol,
                "previous_close": base_price,
                "pre_market_price": round(pre_market_price, 2),
                "pre_market_change": round(pre_market_price - base_price, 2),
                "pre_market_change_pct": round(change_pct, 2),
                "volume_estimate": random.randint(10000, 1000000),
                "news_sentiment": random.choice(["positive", "neutral", "negative"]),
                "analyst_rating": random.choice(["buy", "hold", "sell"])
            }
        
        return pre_market_data
    
    def analyze_market_sentiment(self, pre_market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场情绪"""
        positive_count = 0
        negative_count = 0
        total_stocks = len(pre_market_data)
        
        for symbol, data in pre_market_data.items():
            if data["pre_market_change_pct"] > 0:
                positive_count += 1
            elif data["pre_market_change_pct"] < 0:
                negative_count += 1
        
        overall_sentiment = "neutral"
        if positive_count > negative_count * 1.5:
            overall_sentiment = "bullish"
        elif negative_count > positive_count * 1.5:
            overall_sentiment = "bearish"
        
        return {
            "overall_sentiment": overall_sentiment,
            "positive_stocks": positive_count,
            "negative_stocks": negative_count,
            "neutral_stocks": total_stocks - positive_count - negative_count,
            "market_breadth": round(positive_count / total_stocks * 100, 1)
        }
    
    def generate_trading_signals(self, pre_market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成交易信号"""
        signals = []
        
        for symbol, data in pre_market_data.items():
            signal = {
                "symbol": symbol,
                "action": "hold",
                "confidence": "low",
                "reason": "",
                "target_price": None,
                "stop_loss": None
            }
            
            # 简单的信号生成逻辑
            if data["pre_market_change_pct"] > 1.5 and data["news_sentiment"] == "positive":
                signal["action"] = "buy"
                signal["confidence"] = "high"
                signal["reason"] = "Strong pre-market momentum with positive news"
                signal["target_price"] = round(data["pre_market_price"] * 1.03, 2)
                signal["stop_loss"] = round(data["pre_market_price"] * 0.97, 2)
            elif data["pre_market_change_pct"] < -1.5 and data["news_sentiment"] == "negative":
                signal["action"] = "sell"
                signal["confidence"] = "high"
                signal["reason"] = "Weak pre-market performance with negative news"
                signal["target_price"] = round(data["pre_market_price"] * 0.97, 2)
                signal["stop_loss"] = round(data["pre_market_price"] * 1.03, 2)
            elif abs(data["pre_market_change_pct"]) > 0.5:
                signal["action"] = "watch"
                signal["confidence"] = "medium"
                signal["reason"] = "Moderate pre-market movement"
            
            signals.append(signal)
        
        return signals
    
    def run(self) -> Dict[str, Any]:
        """执行盘前监控任务"""
        print("🚀 开始执行股票监控系统 - 盘前任务")
        
        # 获取当前时间信息
        datetime_info = self.get_current_datetime_info()
        print(f"📅 当前时间: {datetime_info['datetime']}")
        print(f"📊 交易日: {'是' if datetime_info['is_trading_day'] else '否'}")
        
        if not datetime_info['is_trading_day']:
            result = {
                "status": "skipped",
                "message": "今天不是交易日，跳过盘前任务",
                "datetime_info": datetime_info
            }
            return result
        
        # 获取盘前数据
        print("📈 获取盘前数据...")
        pre_market_data = self.simulate_pre_market_data()
        
        # 分析市场情绪
        print("🧠 分析市场情绪...")
        market_sentiment = self.analyze_market_sentiment(pre_market_data)
        
        # 生成交易信号
        print("🎯 生成交易信号...")
        trading_signals = self.generate_trading_signals(pre_market_data)
        
        # 准备结果
        result = {
            "status": "completed",
            "datetime_info": datetime_info,
            "pre_market_data": pre_market_data,
            "market_sentiment": market_sentiment,
            "trading_signals": trading_signals,
            "execution_time": datetime.datetime.now().isoformat()
        }
        
        # 保存结果到文件
        result_file = os.path.join(
            self.results_dir, 
            f"stock_pre_market_{datetime_info['date']}.json"
        )
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 盘前任务完成！结果已保存到: {result_file}")
        return result

if __name__ == "__main__":
    monitor = StockMonitorPreMarket()
    result = monitor.run()
    
    # 输出简要摘要
    if result["status"] == "completed":
        sentiment = result["market_sentiment"]
        signals = result["trading_signals"]
        
        buy_signals = [s for s in signals if s["action"] == "buy"]
        sell_signals = [s for s in signals if s["action"] == "sell"]
        watch_signals = [s for s in signals if s["action"] == "watch"]
        
        print("\n📋 盘前任务摘要:")
        print(f"   📊 市场情绪: {sentiment['overall_sentiment']}")
        print(f"   📈 上涨股票: {sentiment['positive_stocks']}")
        print(f"   📉 下跌股票: {sentiment['negative_stocks']}")
        print(f"   ⚖️  市场广度: {sentiment['market_breadth']}%")
        print(f"   💰 买入信号: {len(buy_signals)}")
        print(f"   📤 卖出信号: {len(sell_signals)}")
        print(f"   👀 观察信号: {len(watch_signals)}")