#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlobalTokenHub - 交易引擎 V2 (修复版)
修复订单撮合逻辑
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(Enum):
    PENDING = "pending"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    order_id: str
    user_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    price: Optional[float]
    quantity: float
    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.order_id is None:
            self.order_id = str(uuid.uuid4())
    
    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity
    
    @property
    def is_active(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIAL_FILLED]


@dataclass
class Trade:
    trade_id: str
    symbol: str
    buyer_order_id: str
    seller_order_id: str
    price: float
    quantity: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.trade_id is None:
            self.trade_id = str(uuid.uuid4())


class TradingEngine:
    """交易引擎 V2 - 修复撮合逻辑"""
    
    def __init__(self, fee_rate: float = 0.001):
        self.fee_rate = fee_rate
        self.symbols: List[str] = []
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        
        # 订单簿：{symbol: {bids: [(price, qty, order_id)], asks: [(price, qty, order_id)]}}
        self.order_books: Dict[str, Dict] = {}
        
        logger.info(f"交易引擎 V2 已初始化")
    
    def add_symbol(self, symbol: str, base: str, quote: str):
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.order_books[symbol] = {'bids': [], 'asks': []}
            logger.info(f"添加交易对：{symbol}")
    
    def submit_order(self, order: Order) -> Tuple[bool, str]:
        """提交订单 - 先撮合，后挂单"""
        if order.quantity <= 0:
            return False, "数量必须大于 0"
        
        if order.symbol not in self.symbols:
            return False, f"交易对不存在：{order.symbol}"
        
        # 保存订单
        self.orders[order.order_id] = order
        logger.info(f"订单提交：{order.order_id[:8]}... - {order.side.value} {order.quantity} @ {order.price}")
        
        # 执行撮合
        trades = self._match_order(order)
        
        # 更新订单状态
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
            logger.info(f"✅ 订单完全成交：{order.filled_quantity}/{order.quantity}")
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIAL_FILLED
            logger.info(f"⚡ 订单部分成交：{order.filled_quantity}/{order.quantity}")
        else:
            # 未成交，挂到订单簿
            if order.type == OrderType.LIMIT and order.price:
                self._add_to_book(order)
                order.status = OrderStatus.PENDING
                logger.info(f"📋 订单挂单：{order.quantity} @ {order.price}")
        
        return True, f"订单已提交：{order.order_id}"
    
    def _match_order(self, order: Order) -> List[Trade]:
        """撮合订单"""
        trades = []
        book = self.order_books[order.symbol]
        
        if order.side == OrderSide.BUY:
            # 买单：匹配卖单（从低价到高价）
            book['asks'].sort(key=lambda x: x[0])  # 按价格升序
            
            i = 0
            while i < len(book['asks']) and order.remaining_quantity > 0:
                ask_price, ask_qty, ask_order_id = book['asks'][i]
                
                # 限价单：买价必须 >= 卖价
                if order.type == OrderType.LIMIT and order.price < ask_price:
                    break
                
                # 计算成交量
                fill_qty = min(order.remaining_quantity, ask_qty)
                
                # 创建成交记录
                trade = Trade(
                    trade_id=None,
                    symbol=order.symbol,
                    buyer_order_id=order.order_id,
                    seller_order_id=ask_order_id,
                    price=ask_price,
                    quantity=fill_qty
                )
                trades.append(trade)
                
                # 更新订单
                order.filled_quantity += fill_qty
                
                # 更新卖单
                book['asks'][i] = (ask_price, ask_qty - fill_qty, ask_order_id)
                if book['asks'][i][1] <= 0:
                    book['asks'].pop(i)
                else:
                    i += 1
                
                logger.info(f"💰 成交：{fill_qty} @ ${ask_price:,.2f}")
        
        else:
            # 卖单：匹配买单（从高价到低价）
            book['bids'].sort(key=lambda x: x[0], reverse=True)  # 按价格降序
            
            i = 0
            while i < len(book['bids']) and order.remaining_quantity > 0:
                bid_price, bid_qty, bid_order_id = book['bids'][i]
                
                # 限价单：卖价必须 <= 买价
                if order.type == OrderType.LIMIT and order.price > bid_price:
                    break
                
                # 计算成交量
                fill_qty = min(order.remaining_quantity, bid_qty)
                
                # 创建成交记录
                trade = Trade(
                    trade_id=None,
                    symbol=order.symbol,
                    buyer_order_id=bid_order_id,
                    seller_order_id=order.order_id,
                    price=bid_price,
                    quantity=fill_qty
                )
                trades.append(trade)
                
                # 更新订单
                order.filled_quantity += fill_qty
                
                # 更新买单
                book['bids'][i] = (bid_price, bid_qty - fill_qty, bid_order_id)
                if book['bids'][i][1] <= 0:
                    book['bids'].pop(i)
                else:
                    i += 1
                
                logger.info(f"💰 成交：{fill_qty} @ ${bid_price:,.2f}")
        
        self.trades.extend(trades)
        return trades
    
    def _add_to_book(self, order: Order):
        """添加订单到订单簿"""
        book = self.order_books[order.symbol]
        
        if order.side == OrderSide.BUY:
            book['bids'].append((order.price, order.remaining_quantity, order.order_id))
        else:
            book['asks'].append((order.price, order.remaining_quantity, order.order_id))
    
    def get_order_book(self, symbol: str, depth: int = 10) -> Dict:
        """获取订单簿"""
        if symbol not in self.order_books:
            return {"error": "交易对不存在"}
        
        book = self.order_books[symbol]
        
        bids = sorted(book['bids'], key=lambda x: x[0], reverse=True)[:depth]
        asks = sorted(book['asks'], key=lambda x: x[0])[:depth]
        
        return {
            "symbol": symbol,
            "bids": [{"price": p, "quantity": q} for p, q, _ in bids],
            "asks": [{"price": p, "quantity": q} for p, q, _ in asks],
            "best_bid": bids[0][0] if bids else None,
            "best_ask": asks[0][0] if asks else None,
            "spread": (asks[0][0] - bids[0][0]) if (asks and bids) else None
        }
    
    def get_stats(self) -> Dict:
        return {
            "symbols": len(self.symbols),
            "orders": len(self.orders),
            "trades": len(self.trades),
            "active_orders": sum(1 for o in self.orders.values() if o.is_active)
        }


def main():
    print("=" * 60)
    print("🚀 GlobalTokenHub - 交易引擎 V2 测试")
    print("=" * 60)
    
    engine = TradingEngine(fee_rate=0.001)
    engine.add_symbol("BTC/USDT", "BTC", "USDT")
    
    print("\n✅ 交易引擎初始化完成\n")
    
    # 测试 1: 提交卖单
    print("📋 测试 1: 提交卖单 (0.1 BTC @ $50,000)")
    sell1 = Order(None, "user_001", "BTC/USDT", OrderSide.SELL, OrderType.LIMIT, 50000.0, 0.1)
    engine.submit_order(sell1)
    print(f"   状态：{sell1.status.value}\n")
    
    # 测试 2: 提交买单（完全成交）
    print("📋 测试 2: 提交买单 (0.05 BTC @ $50,000 - 期望成交)")
    buy1 = Order(None, "user_002", "BTC/USDT", OrderSide.BUY, OrderType.LIMIT, 50000.0, 0.05)
    engine.submit_order(buy1)
    print(f"   成交：{buy1.filled_quantity} BTC")
    print(f"   状态：{buy1.status.value}\n")
    
    # 测试 3: 提交买单（部分成交）
    print("📋 测试 3: 提交买单 (0.1 BTC @ $50,000 - 期望部分成交)")
    buy2 = Order(None, "user_003", "BTC/USDT", OrderSide.BUY, OrderType.LIMIT, 50000.0, 0.1)
    engine.submit_order(buy2)
    print(f"   成交：{buy2.filled_quantity} BTC")
    print(f"   状态：{buy2.status.value}\n")
    
    # 测试 4: 查看订单簿
    print("📊 测试 4: 查看订单簿")
    book = engine.get_order_book("BTC/USDT")
    print(f"   买单：{len(book['bids'])} 个")
    print(f"   卖单：{len(book['asks'])} 个")
    if book['asks']:
        print(f"   最低卖价：${book['asks'][0]['price']:,.2f}")
    if book['bids']:
        print(f"   最高买价：${book['bids'][0]['price']:,.2f}")
    print()
    
    # 测试 5: 查看成交记录
    print("📜 测试 5: 成交记录")
    print(f"   总成交：{len(engine.trades)} 笔")
    for trade in engine.trades:
        print(f"   - {trade.quantity} BTC @ ${trade.price:,.2f}")
    print()
    
    # 测试 6: 统计
    print("📈 测试 6: 统计信息")
    stats = engine.get_stats()
    print(f"   交易对：{stats['symbols']}")
    print(f"   订单：{stats['orders']}")
    print(f"   成交：{stats['trades']}")
    print(f"   活跃订单：{stats['active_orders']}")
    
    print("\n" + "=" * 60)
    print("✅ 交易引擎 V2 测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
