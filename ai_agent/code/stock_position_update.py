#!/usr/bin/env python3
"""
华联股份持仓状态更新
已减仓5100股，更新持仓和盈亏计算
"""

def update_position():
    """更新持仓状态"""
    
    # 原始持仓信息
    original_shares = 13500  # 原始持仓数量
    cost_price = 1.873       # 成本价
    current_price = 1.64     # 当前价格
    
    # 减仓操作
    sold_shares = 5100       # 已减仓数量
    remaining_shares = original_shares - sold_shares
    
    # 计算盈亏
    total_cost = original_shares * cost_price
    current_value = remaining_shares * current_price
    realized_loss = sold_shares * (current_price - cost_price)  # 已实现亏损
    unrealized_loss = remaining_shares * (current_price - cost_price)  # 未实现亏损
    total_loss = realized_loss + unrealized_loss
    
    # 回收资金
    recovered_cash = sold_shares * current_price
    
    print(f"📊 华联股份(000882)持仓更新")
    print("=" * 50)
    print(f"原始持仓: {original_shares:,}股 @ ¥{cost_price}")
    print(f"减仓操作: -{sold_shares:,}股 @ ¥{current_price}")
    print(f"剩余持仓: {remaining_shares:,}股")
    print("-" * 50)
    print(f"💰 回收资金: ¥{recovered_cash:,.2f}")
    print(f"📉 已实现亏损: ¥{realized_loss:,.2f}")
    print(f"📉 未实现亏损: ¥{unrealized_loss:,.2f}")
    print(f"📉 总亏损: ¥{total_loss:,.2f}")
    print(f"💸 亏损比例: {total_loss/(original_shares*cost_price)*100:.1f}%")
    print("=" * 50)
    
    # 风险分析
    print(f"🔍 风险分析")
    print(f"剩余持仓市值: ¥{remaining_shares * current_price:,.2f}")
    print(f"距离止损位(¥1.60): ¥{current_price - 1.60:.2f}")
    
    if current_price < 1.60:
        print(f"🚨 紧急: 股价已跌破止损位!")
        print(f"建议: 考虑进一步减仓或清仓")
    elif current_price < 1.62:
        print(f"⚠️  警告: 股价接近止损位")
        print(f"建议: 密切监控，准备进一步行动")
    else:
        print(f"🟡 观察: 股价在安全区间")
        print(f"建议: 继续持有观察")
    
    # 下一步建议
    print(f"\n🎯 下一步操作建议")
    print(f"1. 监控剩余{remaining_shares:,}股表现")
    print(f"2. 设置¥1.60止损警报")
    print(f"3. 考虑中远海发建仓机会")
    print(f"4. 等待市场情绪好转")

if __name__ == "__main__":
    update_position()