#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急股票止损计划 - 华联股份(000882)
当前股价: ¥1.57，已跌破止损位¥1.60
亏损: -16.18%，持仓13,500股
"""

import json
from datetime import datetime

# 股票信息
stock_info = {
    "code": "000882",
    "name": "华联股份",
    "current_price": 1.57,
    "stop_loss": 1.60,
    "cost_price": 1.873,
    "shares": 13500,
    "profit_loss": -0.303,  # 每股亏损
    "total_loss": -4090.50,  # 总亏损
    "loss_percentage": -16.18
}

# 紧急止损计划
def create_emergency_plan():
    """创建紧急止损交易计划"""
    
    # 减仓70%计算
    reduce_shares = int(stock_info["shares"] * 0.7)  # 9,450股
    remaining_shares = stock_info["shares"] - reduce_shares  # 4,050股
    
    # 预计回收资金
    expected_cash = reduce_shares * stock_info["current_price"]
    
    plan = {
        "emergency_level": "CRITICAL",
        "reason": "股价已跌破止损位¥1.60，当前¥1.57",
        "action": "立即减仓70%",
        "reduce_shares": reduce_shares,
        "remaining_shares": remaining_shares,
        "expected_cash": round(expected_cash, 2),
        "execution_time": "明日开盘立即执行",
        "risk_after": "持仓风险降低70%",
        "new_cost_basis": "剩余持仓成本需要重新计算",
        "monitoring": "减仓后继续监控，如继续下跌考虑清仓"
    }
    
    return plan

def generate_trading_instructions(plan):
    """生成具体的交易指令"""
    
    instructions = {
        "stock_code": stock_info["code"],
        "stock_name": stock_info["name"],
        "action": "SELL",
        "quantity": plan["reduce_shares"],
        "price_type": "MARKET",  # 市价单
        "time_in_force": "OPEN",  # 开盘立即执行
        "reason": f"紧急止损：跌破止损位¥{stock_info['stop_loss']}，当前¥{stock_info['current_price']}",
        "risk_control": "严格执行止损纪律",
        "follow_up": "执行后立即汇报结果"
    }
    
    return instructions

def main():
    """主函数"""
    print("🚨 紧急股票止损计划")
    print("=" * 50)
    
    # 显示当前持仓情况
    print(f"📊 持仓情况:")
    print(f"   股票: {stock_info['name']}({stock_info['code']})")
    print(f"   持仓: {stock_info['shares']:,}股")
    print(f"   成本价: ¥{stock_info['cost_price']}")
    print(f"   当前价: ¥{stock_info['current_price']} 🔴")
    print(f"   止损位: ¥{stock_info['stop_loss']}")
    print(f"   亏损: ¥{stock_info['total_loss']:,.2f} ({stock_info['loss_percentage']}%)")
    print()
    
    # 生成紧急计划
    plan = create_emergency_plan()
    
    print(f"🚀 紧急止损计划:")
    print(f"   紧急级别: {plan['emergency_level']}")
    print(f"   原因: {plan['reason']}")
    print(f"   行动: {plan['action']}")
    print(f"   减仓数量: {plan['reduce_shares']:,}股")
    print(f"   剩余持仓: {plan['remaining_shares']:,}股")
    print(f"   预计回收资金: ¥{plan['expected_cash']:,.2f}")
    print(f"   执行时间: {plan['execution_time']}")
    print(f"   风险控制: {plan['risk_after']}")
    print()
    
    # 生成交易指令
    instructions = generate_trading_instructions(plan)
    
    print(f"📋 具体交易指令:")
    for key, value in instructions.items():
        print(f"   {key}: {value}")
    
    # 保存计划文件
    output = {
        "timestamp": datetime.now().isoformat(),
        "stock_info": stock_info,
        "emergency_plan": plan,
        "trading_instructions": instructions
    }
    
    with open("/root/.openclaw/workspace/ai_agent/results/emergency_stock_plan_2026-04-05.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print()
    print("✅ 紧急止损计划已生成并保存")
    print("📁 文件: /root/.openclaw/workspace/ai_agent/results/emergency_stock_plan_2026-04-05.json")
    print("⏰ 请明日开盘立即执行！")

if __name__ == "__main__":
    main()