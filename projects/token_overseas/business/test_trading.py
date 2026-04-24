#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易引擎完整测试
测试订单撮合、订单簿管理等核心功能
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/projects/token_overseas/business')

from trading_engine import TradingEngine, Order, OrderSide, OrderType

print("=" * 60)
print("🚀 GlobalTokenHub - 交易引擎完整测试")
print("=" * 60)

# 创建交易引擎
engine = TradingEngine(fee_rate=0.001)

# 添加交易对
engine.add_symbol("BTC/USDT", "BTC", "USDT")
print("\n✅ 交易引擎初始化完成")
print(f"交易对：{engine.symbols}")

# 测试 1: 提交卖单
print("\n📋 测试 1: 提交卖单")
sell_order1 = Order(
    order_id=None,
    user_id="user_001",
    symbol="BTC/USDT",
    side=OrderSide.SELL,
    type=OrderType.LIMIT,
    price=50000.0,
    quantity=0.1
)
success, msg = engine.submit_order(sell_order1)
print(f"  卖单 1: {msg}")
print(f"  状态：{sell_order1.status.value}")

# 测试 2: 提交另一个卖单
print("\n📋 测试 2: 提交另一个卖单")
sell_order2 = Order(
    order_id=None,
    user_id="user_001",
    symbol="BTC/USDT",
    side=OrderSide.SELL,
    type=OrderType.LIMIT,
    price=50100.0,
    quantity=0.2
)
success, msg = engine.submit_order(sell_order2)
print(f"  卖单 2: {msg}")

# 测试 3: 提交买单（部分成交）
print("\n📋 测试 3: 提交买单（期望成交）")
buy_order1 = Order(
    order_id=None,
    user_id="user_002",
    symbol="BTC/USDT",
    side=OrderSide.BUY,
    type=OrderType.LIMIT,
    price=50000.0,
    quantity=0.05  # 买入 0.05，与卖单 1 成交
)
success, msg = engine.submit_order(buy_order1)
print(f"  买单 1: {msg}")
print(f"  成交数量：{buy_order1.filled_quantity}")
print(f"  订单状态：{buy_order1.status.value}")

# 测试 4: 提交买单（完全成交）
print("\n📋 测试 4: 提交买单（期望完全成交）")
buy_order2 = Order(
    order_id=None,
    user_id="user_003",
    symbol="BTC/USDT",
    side=OrderSide.BUY,
    type=OrderType.LIMIT,
    price=50000.0,
    quantity=0.05  # 买入 0.05，与卖单 1 剩余部分成交
)
success, msg = engine.submit_order(buy_order2)
print(f"  买单 2: {msg}")
print(f"  成交数量：{buy_order2.filled_quantity}")
print(f"  订单状态：{buy_order2.status.value}")

# 测试 5: 获取订单簿
print("\n📊 测试 5: 获取订单簿")
order_book = engine.get_order_book("BTC/USDT")
print(f"  交易对：{order_book['symbol']}")
print(f"  买单数量：{len(order_book['bids'])}")
print(f"  卖单数量：{len(order_book['asks'])}")
if order_book['asks']:
    print(f"  最低卖价：${order_book['asks'][0]['price']:,.2f} x {order_book['asks'][0]['quantity']}")
if order_book['bids']:
    print(f"  最高买价：${order_book['bids'][0]['price']:,.2f} x {order_book['bids'][0]['quantity']}")

# 测试 6: 获取行情
print("\n💹 测试 6: 获取行情")
ticker = engine.get_ticker("BTC/USDT")
print(f"  最新价：${ticker.get('last', 0):,.2f}")
print(f"  24h 成交量：{ticker.get('volume_24h', 0):,.4f} BTC")

# 测试 7: 交易统计
print("\n📈 测试 7: 交易统计")
stats = engine.get_stats()
print(f"  总成交数：{stats['total_trades']}")
print(f"  活跃订单：{stats['active_orders']}")
print(f"  订单总数：{stats['orders_count']}")

# 测试 8: 查看成交记录
print("\n📜 测试 8: 成交记录")
print(f"  总成交笔数：{len(engine.trades)}")
for i, trade in enumerate(engine.trades[:5], 1):
    print(f"  成交{i}: {trade.quantity} BTC @ ${trade.price:,.2f} = ${trade.price*trade.quantity:,.2f}")

print("\n" + "=" * 60)
print("✅ 交易引擎测试完成!")
print("=" * 60)
