#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抄底计划执行脚本 - 士兰微 + 华联为主
"""

import json
from datetime import datetime

# 调整后的抄底计划
COPY_PLAN = {
    "total_capital": 1000000,  # 总资金 100 万
    "phase": "first",
    "focus": "士兰微 + 华联股份",
    
    "stocks": [
        {
            "code": "600460",
            "name": "士兰微",
            "priority": 1,
            "current_price": 29.50,
            "buy_range": (28, 30),
            "position_percent": 0.35,
            "stop_loss": 26,
            "target": 35,
            "add_position": 27
        },
        {
            "code": "600361",
            "name": "华联股份",
            "priority": 2,
            "current_price": 2.95,
            "buy_range": (2.8, 3.0),
            "position_percent": 0.25,
            "stop_loss": 2.5,
            "target": 3.5,
            "add_position": 2.6
        },
        {
            "code": "002594",
            "name": "比亚迪",
            "priority": 3,
            "current_price": 108.53,
            "buy_range": (105, 108),
            "position_percent": 0.10,
            "stop_loss": 95,
            "target": 120
        },
        {
            "code": "600519",
            "name": "贵州茅台",
            "priority": 4,
            "current_price": 1401.70,
            "buy_range": (1380, 1400),
            "position_percent": 0.10,
            "stop_loss": 1300,
            "target": 1600
        }
    ]
}

def calculate_orders():
    """计算买入订单"""
    total_capital = COPY_PLAN["total_capital"]
    
    print("=" * 80)
    print("🎯 抄底计划 - 买入订单计算（士兰微 + 华联为主）")
    print("=" * 80)
    print(f"总资金：¥{total_capital:,.0f}")
    print(f"主力建仓：士兰微 (35%) + 华联股份 (25%) = 60%")
    print(f"辅助建仓：比亚迪 (10%) + 贵州茅台 (10%) = 20%")
    print(f"现金保留：20%")
    print("=" * 80)
    
    orders = []
    total_amount = 0
    
    for stock in COPY_PLAN["stocks"]:
        amount = total_capital * stock["position_percent"]
        buy_price = (stock["buy_range"][0] + stock["buy_range"][1]) / 2
        
        # 计算股数（100 股的整数倍）
        if stock["code"] == "600361":  # 华联股价低，按金额计算
            volume = int(amount / buy_price / 100) * 100
        else:
            volume = int(amount / buy_price / 100) * 100
        
        actual_amount = volume * buy_price
        total_amount += actual_amount
        
        risk_percent = (buy_price - stock["stop_loss"]) / buy_price * 100
        target_percent = (stock["target"] - buy_price) / buy_price * 100
        
        order = {
            "priority": stock["priority"],
            "code": stock["code"],
            "name": stock["name"],
            "volume": volume,
            "price": buy_price,
            "amount": actual_amount,
            "stop_loss": stock["stop_loss"],
            "target": stock["target"],
            "risk_percent": risk_percent,
            "target_percent": target_percent
        }
        orders.append(order)
        
        # 打印订单详情
        priority_flag = "🔥" if stock["priority"] <= 2 else "  "
        print(f"\n{priority_flag} {stock['priority']}. {stock['code']} {stock['name']}")
        print(f"   当前价：¥{stock['current_price']:.2f}")
        print(f"   买入区间：¥{stock['buy_range'][0]:.2f} - ¥{stock['buy_range'][1]:.2f}")
        print(f"   建议买入：¥{buy_price:.2f}")
        print(f"   数量：{volume:,} 股")
        print(f"   金额：¥{actual_amount:,.0f} ({stock['position_percent']*100:.0f}%)")
        print(f"   止损：¥{stock['stop_loss']:.2f} (-{risk_percent:.1f}%)")
        print(f"   目标：¥{stock['target']:.2f} (+{target_percent:.1f}%)")
        if "add_position" in stock:
            print(f"   加仓位：¥{stock['add_position']:.2f}")
    
    remaining = total_capital * 0.20  # 20% 现金保留
    
    print("\n" + "=" * 80)
    print(f"总计：¥{total_amount:,.0f} / ¥{total_capital * 0.8:,.0f}")
    print(f"现金保留：¥{remaining:,.0f} (20%)")
    print("=" * 80)
    
    return orders

def generate_order_file(orders):
    """生成订单文件"""
    order_data = {
        "timestamp": datetime.now().isoformat(),
        "strategy": "士兰微 + 华联股份为主",
        "total_capital": COPY_PLAN["total_capital"],
        "phase": COPY_PLAN["phase"],
        "orders": orders
    }
    
    filename = f"/root/.openclaw/workspace/reports/BUY_ORDERS_ADJUSTED_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(order_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 订单已保存：{filename}")
    return filename

def main():
    """主函数"""
    print("\n" + "🚀" * 40)
    print("抄底计划执行脚本 - 调整版（士兰微 + 华联为主）")
    print("🚀" * 40 + "\n")
    
    # 计算订单
    orders = calculate_orders()
    
    # 生成订单文件
    generate_order_file(orders)
    
    # 风险提示
    print("\n" + "⚠️" * 40)
    print("风险警示")
    print("⚠️" * 40)
    print("""
【当前状态】
- 企稳信号：0/4 个（风险高）
- 可能继续下跌：5-10%
- 士兰微：半导体板块被抛售
- 华联股份：消费复苏不确定

【执行方案】
A. 立即执行（14:51）- 高风险
B. 明日开盘（推荐）- 中风险
C. 等企稳信号（最安全）- 低风险

【风控纪律】
1. 严格执行止损
2. 不追涨杀跌
3. 保留 20% 现金
4. 分批建仓

请老大确认执行方案！
    """)
    print("⚠️" * 40 + "\n")

if __name__ == "__main__":
    main()
