#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略执行器 - 自动执行交易策略
"""

from datetime import datetime
from typing import Dict, List, Optional
import json

class StrategyExecutor:
    """策略执行器"""
    
    def __init__(self, broker_api, risk_control):
        self.broker = broker_api
        self.risk = risk_control
        self.strategies = {}
        self.running = False
    
    def add_strategy(self, strategy_id: str, strategy_config: Dict):
        """添加策略"""
        self.strategies[strategy_id] = {
            "config": strategy_config,
            "status": "stopped",
            "last_run": None,
            "positions": {}
        }
    
    def start_strategy(self, strategy_id: str) -> bool:
        """启动策略"""
        if strategy_id not in self.strategies:
            return False
        self.strategies[strategy_id]["status"] = "running"
        return True
    
    def stop_strategy(self, strategy_id: str) -> bool:
        """停止策略"""
        if strategy_id not in self.strategies:
            return False
        self.strategies[strategy_id]["status"] = "stopped"
        return True
    
    def execute_signal(self, strategy_id: str, signal: Dict) -> Dict:
        """执行交易信号"""
        if strategy_id not in self.strategies:
            return {"success": False, "error": "策略不存在"}
        
        strategy = self.strategies[strategy_id]
        if strategy["status"] != "running":
            return {"success": False, "error": "策略未启动"}
        
        # 检查风控
        if signal["action"] == "buy":
            check = self.risk.check_position_limit(0.5, 0.1)  # 简化
            if not check["allowed"]:
                return {"success": False, "error": check["reason"]}
        
        # 执行交易
        try:
            if signal["action"] == "buy":
                result = self.broker.buy(
                    signal["stock_code"],
                    signal["volume"],
                    signal.get("price")
                )
            else:
                result = self.broker.sell(
                    signal["stock_code"],
                    signal["volume"],
                    signal.get("price")
                )
            
            # 更新策略持仓
            if result.get("success"):
                self._update_position(strategy_id, signal, result)
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _update_position(self, strategy_id: str, signal: Dict, result: Dict):
        """更新策略持仓"""
        strategy = self.strategies[strategy_id]
        code = signal["stock_code"]
        
        if code not in strategy["positions"]:
            strategy["positions"][code] = {"volume": 0, "cost": 0}
        
        pos = strategy["positions"][code]
        if signal["action"] == "buy":
            total_cost = pos["cost"] * pos["volume"] + result["price"] * signal["volume"]
            pos["volume"] += signal["volume"]
            pos["cost"] = total_cost / pos["volume"] if pos["volume"] > 0 else 0
        else:
            pos["volume"] -= signal["volume"]
            if pos["volume"] <= 0:
                del strategy["positions"][code]
    
    def monitor_positions(self):
        """监控持仓，检查止损止盈"""
        signals = []
        
        for strategy_id, strategy in self.strategies.items():
            if strategy["status"] != "running":
                continue
            
            for code, pos in strategy["positions"].items():
                # 获取当前价格
                quote = self.broker.get_quote(code)
                if not quote:
                    continue
                
                current_price = quote["price"]
                
                # 检查止损止盈
                check = self.risk.check_stop_loss(code, current_price, pos["cost"])
                
                if check["triggered"]:
                    signals.append({
                        "strategy_id": strategy_id,
                        "stock_code": code,
                        "action": "sell",
                        "volume": pos["volume"],
                        "reason": check["message"],
                        "type": check["type"]
                    })
        
        return signals
    
    def get_strategy_status(self, strategy_id: str = None) -> Dict:
        """获取策略状态"""
        if strategy_id:
            return self.strategies.get(strategy_id, {})
        return self.strategies

# 策略信号生成器
class SignalGenerator:
    """信号生成器 - 根据技术指标生成交易信号"""
    
    @staticmethod
    def ma_cross(prices: List[float], short_period: int = 5, long_period: int = 20) -> str:
        """均线交叉信号"""
        if len(prices) < long_period:
            return "hold"
        
        short_ma = sum(prices[-short_period:]) / short_period
        long_ma = sum(prices[-long_period:]) / long_period
        
        prev_short_ma = sum(prices[-short_period-1:-1]) / short_period
        prev_long_ma = sum(prices[-long_period-1:-1]) / long_period
        
        # 金叉
        if short_ma > long_ma and prev_short_ma <= prev_long_ma:
            return "buy"
        # 死叉
        elif short_ma < long_ma and prev_short_ma >= prev_long_ma:
            return "sell"
        
        return "hold"
    
    @staticmethod
    def rsi_signal(prices: List[float], period: int = 14, oversold: float = 30, overbought: float = 70) -> str:
        """RSI 信号"""
        if len(prices) < period + 1:
            return "hold"
        
        gains = []
        losses = []
        
        for i in range(1, period + 1):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        if rsi < oversold:
            return "buy"  # 超卖
        elif rsi > overbought:
            return "sell"  # 超买
        
        return "hold"
    
    @staticmethod
    def macd_signal(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> str:
        """MACD 信号（简化版）"""
        if len(prices) < slow + signal:
            return "hold"
        
        # 简化 MACD 计算
        ema_fast = sum(prices[-fast:]) / fast
        ema_slow = sum(prices[-slow:]) / slow
        macd = ema_fast - ema_slow
        
        # 判断趋势
        if macd > 0:
            return "buy"
        elif macd < 0:
            return "sell"
        
        return "hold"