#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控服务 - 止损止盈、风险控制
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

class RiskControl:
    """风控管理器"""
    
    def __init__(self):
        # 默认风控参数
        self.stop_loss_percent = 0.05  # 止损 5%
        self.stop_profit_percent = 0.10  # 止盈 10%
        self.max_position_percent = 0.30  # 单只股票最多 30% 仓位
        self.max_total_position = 0.80  # 最多 80% 仓位
        self.daily_loss_limit = 0.03  # 单日亏损限制 3%
        
        # 持仓监控
        self.positions_monitor = {}
        
    def set_stop_loss(self, stock_code: str, percent: float = 0.05):
        """设置单只股票止损"""
        self.positions_monitor[stock_code] = {
            "stop_loss": percent,
            "stop_profit": self.stop_profit_percent,
            "enabled": True
        }
        return True
    
    def check_stop_loss(self, stock_code: str, current_price: float, cost_price: float) -> Dict:
        """检查是否触发止损"""
        if stock_code not in self.positions_monitor:
            return {"triggered": False, "type": None}
        
        monitor = self.positions_monitor[stock_code]
        if not monitor.get("enabled", False):
            return {"triggered": False, "type": None}
        
        # 计算盈亏比例
        profit_percent = (current_price - cost_price) / cost_price
        
        # 检查止损
        if profit_percent <= -monitor["stop_loss"]:
            return {
                "triggered": True,
                "type": "stop_loss",
                "loss_percent": profit_percent,
                "message": f"触发止损！亏损 {abs(profit_percent)*100:.2f}%"
            }
        
        # 检查止盈
        if profit_percent >= monitor["stop_profit"]:
            return {
                "triggered": True,
                "type": "stop_profit",
                "profit_percent": profit_percent,
                "message": f"触发止盈！盈利 {profit_percent*100:.2f}%"
            }
        
        return {"triggered": False, "type": None}
    
    def check_position_limit(self, current_position_percent: float, buy_percent: float) -> Dict:
        """检查仓位限制"""
        new_position = current_position_percent + buy_percent
        
        if new_position > self.max_total_position:
            return {
                "allowed": False,
                "reason": f"超过总仓位限制 ({self.max_total_position*100}%)",
                "max_allowed": self.max_total_position - current_position_percent
            }
        
        if buy_percent > self.max_position_percent:
            return {
                "allowed": False,
                "reason": f"单只股票超过仓位限制 ({self.max_position_percent*100}%)",
                "max_allowed": self.max_position_percent
            }
        
        return {"allowed": True}
    
    def get_risk_report(self, positions: List[Dict], current_prices: Dict[str, float]) -> Dict:
        """生成风控报告"""
        report = {
            "total_positions": len(positions),
            "positions": [],
            "warnings": [],
            "total_profit": 0.0
        }
        
        for pos in positions:
            code = pos["stock_code"]
            current_price = current_prices.get(code, pos["cost_price"])
            profit_percent = (current_price - pos["cost_price"]) / pos["cost_price"]
            
            pos_report = {
                "code": code,
                "name": pos.get("stock_name", ""),
                "volume": pos["volume"],
                "cost_price": pos["cost_price"],
                "current_price": current_price,
                "profit_percent": profit_percent,
                "profit_amount": (current_price - pos["cost_price"]) * pos["volume"]
            }
            
            # 检查止损止盈
            check_result = self.check_stop_loss(code, current_price, pos["cost_price"])
            if check_result["triggered"]:
                report["warnings"].append(f"⚠️ {code}: {check_result['message']}")
            
            report["positions"].append(pos_report)
            report["total_profit"] += pos_report["profit_amount"]
        
        return report

# 全局风控实例
risk_control = RiskControl()
