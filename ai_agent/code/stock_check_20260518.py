#!/usr/bin/env python3
"""华联股份 000882 持仓检查 - 2026-05-18"""

# 持仓数据
shares = 13500
cost_price = 1.873
stop_loss = 1.60
current_price = 1.53  # 最新价 (2026-05-15 收盘)
prev_close = 1.56
change = -0.03
change_pct = -1.92
high = 1.56
low = 1.52
volume = 465320  # 手

# 计算盈亏
total_cost = shares * cost_price
current_value = shares * current_price
profit_loss = current_value - total_cost
profit_loss_pct = (current_price - cost_price) / cost_price * 100
stop_loss_amount = (stop_loss - cost_price) / cost_price * 100

# 止损线状态
below_stop = current_price <= stop_loss
distance_to_stop = ((current_price - stop_loss) / stop_loss) * 100

print("=" * 60)
print("📊 华联股份 (000882) 持仓检查报告")
print(f"📅 日期: 2026-05-18 08:00 (数据基于 2026-05-15 收盘)")
print("=" * 60)
print(f"\n💰 持仓概况:")
print(f"   持仓数量: {shares:,} 股")
print(f"   成本价:   ¥{cost_price:.3f}")
print(f"   最新价:   ¥{current_price:.3f}")
print(f"   昨收:     ¥{prev_close:.3f}")
print(f"   当日变动: {change:+.2f} ({change_pct:+.2f}%)")
print(f"   日内区间: ¥{low:.2f} ~ ¥{high:.2f}")
print(f"   成交量:   {volume:,} 手")

print(f"\n📈 盈亏分析:")
print(f"   总成本:   ¥{total_cost:,.2f}")
print(f"   当前市值: ¥{current_value:,.2f}")
print(f"   浮动盈亏: ¥{profit_loss:+,.2f} ({profit_loss_pct:+.2f}%)")

print(f"\n🎯 止损设置:")
print(f"   止损位:   ¥{stop_loss:.2f}")
print(f"   距离止损: ¥{current_price - stop_loss:+.2f} ({distance_to_stop:+.2f}%)")
print(f"   止损亏损: {stop_loss_amount:+.2f}%")

# 状态判断
if below_stop:
    print(f"\n🚨 状态: 已跌破止损位!")
    print(f"   ⚠️  当前价 ¥{current_price} < 止损 ¥{stop_loss}")
    print(f"   ⚠️  建议: 执行止损或评估是否调低止损位")
    print(f"   💡  若未止损: 损失将为 ¥{(current_price - cost_price) * shares:+,.2f}")
    print(f"   💡  若止损执行: 损失为 ¥{(stop_loss - cost_price) * shares:+,.2f}")
else:
    print(f"\n✅ 状态: 尚未触及止损")
    print(f"   安全距离: ¥{current_price - stop_loss:+.2f}")

print(f"\n📉 技术面摘要:")
print(f"   从成本 ¥{cost_price:.3f} → ¥{current_price:.3f}")
print(f"   累计跌幅: {abs(profit_loss_pct):.2f}%")
loss_yuan = profit_loss
print(f"   亏损金额: ¥{abs(loss_yuan):,.2f}")
print(f"\n📝 操作建议:")
if below_stop:
    print(f"   🔴 坚决止损: 执行 ¥{stop_loss:.2f} 止损线")
    print(f"   🟡 接受现实: 亏损 ¥{(stop_loss - cost_price) * shares:+,.2f}")
    print(f"   🟢 等待反弹: 跌破止损后可能技术性反弹，但风险极高")
    print(f"   ⚡ 建议老大尽快决定!")
else:
    print(f"   🟢 继续持有，观察今日走势")

print("=" * 60)
