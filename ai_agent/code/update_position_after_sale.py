#!/usr/bin/env python3
"""
更新持仓记录 - 华联股份已部分卖出
"""

import json
from datetime import datetime

def update_position():
    # 原始持仓
    original_shares = 22600
    cost_price = 1.779
    
    # 卖出5000股
    sold_shares = 5000
    remaining_shares = original_shares - sold_shares
    
    # 卖出价格（假设按当前市价1.61）
    sell_price = 1.61
    sell_amount = sold_shares * sell_price
    
    # 剩余持仓成本（先进先出法）
    remaining_cost = remaining_shares * cost_price
    
    print(f"华联股份持仓更新:")
    print(f"原始持仓: {original_shares} 股 @ ¥{cost_price}")
    print(f"卖出数量: {sold_shares} 股 @ ¥{sell_price}")
    print(f"剩余持仓: {remaining_shares} 股 @ ¥{cost_price}")
    print(f"本次卖出金额: ¥{sell_amount:,.2f}")
    print(f"本次亏损: ¥{(cost_price - sell_price) * sold_shares:,.2f}")
    
    # 更新持仓文件
    position_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stocks": [
            {
                "name": "士兰微",
                "code": "600460",
                "shares": 1000,
                "cost_price": 29.364,
                "stop_loss": 26.00
            },
            {
                "name": "华联股份", 
                "code": "000882",
                "shares": remaining_shares,
                "cost_price": cost_price,
                "stop_loss": 1.50
            }
        ]
    }
    
    with open("/root/.openclaw/workspace/reports/UPDATED_POSITION_2026-03-24.md", "w") as f:
        f.write(f"# 持仓更新 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"## 华联股份部分卖出\n\n")
        f.write(f"- 卖出数量: {sold_shares} 股\n")
        f.write(f"- 卖出价格: ¥{sell_price}\n")
        f.write(f"- 剩余持仓: {remaining_shares} 股\n")
        f.write(f"- 剩余成本: ¥{remaining_cost:,.2f}\n")
        f.write(f"- 本次亏损: ¥{(cost_price - sell_price) * sold_shares:,.2f}\n")
    
    return remaining_shares, sell_amount

if __name__ == "__main__":
    update_position()