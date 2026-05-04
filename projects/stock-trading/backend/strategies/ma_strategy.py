#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
均线策略 - 双均线金叉买入、死叉卖出
"""

from datetime import datetime
from typing import Dict, List, Optional

class MAStrategy:
    """均线策略"""
    
    def __init__(self, short_period=5, long_period=20):
        self.short_period = short_period  # 短期均线
        self.long_period = long_period    # 长期均线
        self.name = f"MA{short_period}/{long_period}双均线策略"
        
    def calculate_ma(self, prices: List[float], period: int) -> Optional[float]:
        """计算均线"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def generate_signal(self, kline_data: List[Dict]) -> Dict:
        """
        生成交易信号
        
        买入信号：短期均线上穿长期均线（金叉）
        卖出信号：短期均线下穿长期均线（死叉）
        """
        if len(kline_data) < self.long_period + 1:
            return {"signal": "hold", "reason": "数据不足"}
        
        # 提取收盘价
        close_prices = [day["close"] for day in kline_data]
        
        # 计算当前均线
        current_short_ma = self.calculate_ma(close_prices, self.short_period)
        current_long_ma = self.calculate_ma(close_prices, self.long_period)
        
        # 计算前一日均线
        prev_short_ma = self.calculate_ma(close_prices[:-1], self.short_period)
        prev_long_ma = self.calculate_ma(close_prices[:-1], self.long_period)
        
        if not all([current_short_ma, current_long_ma, prev_short_ma, prev_long_ma]):
            return {"signal": "hold", "reason": "均线计算失败"}
        
        # 判断金叉死叉
        if prev_short_ma <= prev_long_ma and current_short_ma > current_long_ma:
            return {
                "signal": "buy",
                "reason": f"金叉！MA{self.short_period}({current_short_ma:.2f}) 上穿 MA{self.long_period}({current_long_ma:.2f})",
                "confidence": 0.8
            }
        
        elif prev_short_ma >= prev_long_ma and current_short_ma < current_long_ma:
            return {
                "signal": "sell",
                "reason": f"死叉！MA{self.short_period}({current_short_ma:.2f}) 下穿 MA{self.long_period}({current_long_ma:.2f})",
                "confidence": 0.8
            }
        
        else:
            return {
                "signal": "hold",
                "reason": f"MA{self.short_period}={current_short_ma:.2f}, MA{self.long_period}={current_long_ma:.2f}",
                "confidence": 0.5
            }
    
    def get_params(self) -> Dict:
        """获取策略参数"""
        return {
            "name": self.name,
            "short_period": self.short_period,
            "long_period": self.long_period,
            "type": "trend_following"
        }

# 测试
if __name__ == "__main__":
    # 模拟 K 线数据
    test_data = [
        {"close": 10.0}, {"close": 10.2}, {"close": 10.1}, {"close": 10.3},
        {"close": 10.5}, {"close": 10.4}, {"close": 10.6}, {"close": 10.8},
        {"close": 11.0}, {"close": 10.9}, {"close": 11.1}, {"close": 11.3},
        {"close": 11.5}, {"close": 11.4}, {"close": 11.2}, {"close": 11.0},
        {"close": 10.8}, {"close": 10.6}, {"close": 10.9}, {"close": 11.1},
        {"close": 11.3}, {"close": 11.5}, {"close": 11.7}, {"close": 11.9},
        {"close": 12.1}
    ]
    
    strategy = MAStrategy(5, 10)
    signal = strategy.generate_signal(test_data)
    
    print(f"策略：{strategy.name}")
    print(f"信号：{signal['signal']}")
    print(f"原因：{signal['reason']}")
    print(f"置信度：{signal['confidence']}")
