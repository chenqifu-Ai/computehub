#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抄底计划执行脚本
"""

import json
from datetime import datetime

# 抄底计划配置
COPY_PLAN = {
    "total_capital": 1000000,  # 总资金 100 万
    "phase": "first",  # 第一批
    "phase_percent": 0.30,  # 30%
    
    "stocks": [
        {
            "code": "600519",
            "name": "贵州茅台",
            "current_price": 1401.70,
            "buy_range": (1380, 1400),
            "position_percent": 0.10,
            "stop_loss": 1300,
            "target": 1600
        },
        {
            "code": "300750",
            "name": "宁德时代",
            "current_price": 404.00,
            "buy_range": (390, 400),
            "position_percent": 0.10,
            "stop_loss": 350,
            "target": 500
        },
        {
            "code": "002594",
            "name": "比亚迪",
            "current_price": 108.53,
            "buy_range": (105, 108),
            "position_percent": 0.10,
            "stop_loss": 95,
            "target": 120
        }
    ]
}

def calculate_orders():
    """计算买入订单"""
    total_capital = COPY_PLAN["total_capital"]
    phase_amount = total_capital * COPY_PLAN["phase_percent"]
    
    print("=" * 70)
    print("🎯 抄底计划 - 买入订单计算")
    print("=" * 70)
    print(f"总资金：¥{total_capital:,.0f}")
    print(f"第一批仓位：{COPY_PLAN['phase_percent']*100:.0f}% = ¥{phase_amount:,.0f}")
    print("=" * 70)
    
    orders = []
    
    for stock in COPY_PLAN["stocks"]:
        amount = total_capital * stock["position_percent"]
        buy_price = (stock["buy_range"][0] + stock["buy_range"][1]) / 2
        volume = int(amount / buy_price / 100) * 100  # 100 股的整数倍
        
        order = {
            "code": stock["code"],
            "name": stock["name"],
            "volume": volume,
            "price": buy_price,
            "amount": volume * buy_price,
            "stop_loss": stock["stop_loss"],
            "target": stock["target"],
            "risk": (buy_price - stock["stop_loss"]) / buy_price * 100
        }
        orders.append(order)
        
        print(f"\n📈 {stock['code']} {stock['name']}")
        print(f"   当前价：¥{stock['current_price']:.2f}")
        print(f"   买入区间：¥{stock['buy_range'][0]} - ¥{stock['buy_range'][1]}")
        print(f"   建议买入：¥{buy_price:.2f}")
        print(f"   数量：{volume} 股")
        print(f"   金额：¥{order['amount']:,.0f}")
        print(f"   止损：¥{stock['stop_loss']} (-{order['risk']:.1f}%)")
        print(f"   目标：¥{stock['target']} (+{(stock['target']-buy_price)/buy_price*100:.1f}%)")
    
    total_amount = sum(o["amount"] for o in orders)
    remaining = phase_amount - total_amount
    
    print("\n" + "=" * 70)
    print(f"总计：¥{total_amount:,.0f} / ¥{phase_amount:,.0f}")
    print(f"剩余现金：¥{remaining:,.0f}")
    print(f"现金保留：¥{total_capital - phase_amount:,.0f} ({(total_capital - phase_amount)/total_capital*100:.0f}%)")
    print("=" * 70)
    
    return orders

def generate_order_file(orders):
    """生成订单文件"""
    order_data = {
        "timestamp": datetime.now().isoformat(),
        "phase": COPY_PLAN["phase"],
        "total_capital": COPY_PLAN["total_capital"],
        "orders": orders
    }
    
    filename = f"/root/.openclaw/workspace/reports/BUY_ORDERS_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(order_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 订单已保存：{filename}")
    return filename

def main():
    """主函数"""
    print("\n" + "🚀" * 35)
    print("抄底计划执行脚本")
    print("🚀" * 35 + "\n")
    
    # 计算订单
    orders = calculate_orders()
    
    # 生成订单文件
    generate_order_file(orders)
    
    # 风险提示
    print("\n" + "⚠️" * 35)
    print("风险警示")
    print("⚠️" * 35)
    print("""
1. 当前企稳信号：0/4 个（风险高）
2. 可能继续下跌：5-10%
3. 建议分批买入，不要一次性满仓
4. 严格执行止损纪律
5. 保留 70% 现金

执行方案:
A. 立即执行（高风险）
B. 等明日开盘（推荐）
C. 等企稳信号（最安全）

请老大确认执行方案！
    """)
    print("⚠️" * 35 + "\n")

if __name__ == "__main__":
    main()
