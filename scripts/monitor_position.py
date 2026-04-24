#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓监控脚本 - 修正版
"""

import json
from datetime import datetime

# 持仓数据 - 根据 MEMORY.md 更新
POSITIONS = {
    "000882": {
        "name": "华联股份",
        "volume": 13500,
        "cost": 1.779,
        "stop_loss": 1.60,
        "target": 2.00
    }
    # 士兰微(600460) 已于 2026-03-24 清仓，已移除
}

def check_position(code, current_price):
    """检查持仓状态"""
    pos = POSITIONS.get(code)
    if not pos:
        return None
    
    cost = pos["cost"]
    volume = pos["volume"]
    stop_loss = pos["stop_loss"]
    target = pos["target"]
    
    # 计算盈亏
    profit = (current_price - cost) * volume
    profit_percent = (current_price - cost) / cost * 100
    
    # 检查止损
    if current_price <= stop_loss:
        return {
            "code": code,
            "name": pos["name"],
            "action": "STOP_LOSS",
            "price": current_price,
            "message": f"🔴 触发止损！当前¥{current_price:.3f}，止损¥{stop_loss:.2f}"
        }
    
    # 检查止盈
    if current_price >= target:
        return {
            "code": code,
            "name": pos["name"],
            "action": "TAKE_PROFIT",
            "price": current_price,
            "message": f"💰 触发止盈！当前¥{current_price:.3f}，目标¥{target:.2f}"
        }
    
    # 正常状态
    return {
        "code": code,
        "name": pos["name"],
        "action": "HOLD",
        "price": current_price,
        "profit": profit,
        "profit_percent": profit_percent,
        "message": f"{'🟢' if profit > 0 else '🔴' if profit < 0 else '⚪'} {pos['name']}: ¥{current_price:.3f}, 盈亏¥{profit:.2f} ({profit_percent:+.2f}%)"
    }

def main():
    """主函数"""
    print("=" * 70)
    print("📊 持仓监控")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    total_cost = 0
    total_value = 0
    total_profit = 0
    
    for code, pos in POSITIONS.items():
        # 模拟当前价格（实际应从 API 获取）
        # 这里用成本价±小幅波动模拟
        import random
        current_price = pos["cost"] * (1 + random.uniform(-0.05, 0.05))
        
        result = check_position(code, current_price)
        print(result["message"])
        
        if result["action"] == "STOP_LOSS":
            print(f"   ⚠️ 建议：立即卖出 {pos['volume']} 股！")
        elif result["action"] == "TAKE_PROFIT":
            print(f"   ⚠️ 建议：止盈卖出 {pos['volume']} 股！")
        
        total_cost += pos["cost"] * pos["volume"]
        total_value += current_price * pos["volume"]
        total_profit += (current_price - pos["cost"]) * pos["volume"]
    
    print("=" * 70)
    print(f"总成本：¥{total_cost:,.2f}")
    print(f"总市值：¥{total_value:,.2f}")
    print(f"总盈亏：¥{total_profit:,.2f} ({total_profit/total_cost*100:+.2f}%)")
    print("=" * 70)

if __name__ == "__main__":
    main()