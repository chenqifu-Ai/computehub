#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlobalTokenHub - 交易引擎核心模块
Trading Engine Core Module

创建时间：2026-04-19
作者：小智 (运营智能体)
版本：v1.0

功能:
- 订单簿管理
- 订单撮合引擎
- 交易执行
- 价格发现
"""

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import heapq
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """订单类型"""
    LIMIT = "limit"      # 限价单
    MARKET = "market"    # 市价单
    STOP_LOSS = "stop_loss"  # 止损单
    TAKE_PROFIT = "take_profit"  # 止盈单


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"        # 待成交
    PARTIAL_FILLED = "partial_filled"  # 部分成交
    FILLED = "filled"          # 完全成交
    CANCELLED = "cancelled"    # 已取消
    REJECTED = "rejected"      # 已拒绝


class TimeInForce(Enum):
    """订单有效期"""
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill


@dataclass
class Order:
    """订单数据结构"""
    order_id: str
    user_id: str
    symbol: str  # 交易对，如 BTC/USDT
    side: OrderSide
    type: OrderType
    price: Optional[float]  # 限价单价格
    quantity: float  # 数量
    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: TimeInForce = TimeInForce.GTC
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    fee: float = 0.0  # 手续费
    fee_currency: str = "USDT"
    
    def __post_init__(self):
        if self.order_id is None:
            self.order_id = str(uuid.uuid4())
    
    @property
    def remaining_quantity(self) -> float:
        """剩余未成交数量"""
        return self.quantity - self.filled_quantity
    
    @property
    def is_active(self) -> bool:
        """订单是否活跃"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIAL_FILLED]


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    symbol: str
    buyer_order_id: str
    seller_order_id: str
    buyer_user_id: str
    seller_user_id: str
    price: float
    quantity: float
    fee: float
    fee_currency: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.trade_id is None:
            self.trade_id = str(uuid.uuid4())


@dataclass
class OrderBook:
    """订单簿"""
    symbol: str
    bids: List[Tuple[float, float]] = field(default_factory=list)  # 买单 [(价格，数量), ...]
    asks: List[Tuple[float, float]] = field(default_factory=list)  # 卖单 [(价格，数量), ...]
    
    def get_best_bid(self) -> Optional[float]:
        """获取最高买价"""
        if self.bids:
            return max(price for price, qty in self.bids if qty > 0)
        return None
    
    def get_best_ask(self) -> Optional[float]:
        """获取最低卖价"""
        if self.asks:
            return min(price for price, qty in self.asks if qty > 0)
        return None
    
    def get_mid_price(self) -> Optional[float]:
        """获取中间价"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return None
    
    def get_spread(self) -> Optional[float]:
        """获取价差"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None


class TradingEngine:
    """
    交易引擎核心类
    
    功能:
    - 订单簿管理
    - 订单撮合
    - 交易执行
    - 手续费计算
    """
    
    def __init__(self, fee_rate: float = 0.001):
        """
        初始化交易引擎
        
        Args:
            fee_rate: 默认手续费率 (0.1%)
        """
        self.fee_rate = fee_rate
        
        # 订单簿字典 {symbol: OrderBook}
        self.order_books: Dict[str, OrderBook] = {}
        
        # 订单字典 {order_id: Order}
        self.orders: Dict[str, Order] = {}
        
        # 用户订单索引 {user_id: [order_ids]}
        self.user_orders: Dict[str, List[str]] = defaultdict(list)
        
        # 成交记录
        self.trades: List[Trade] = []
        
        # 交易对列表
        self.symbols: List[str] = []
        
        # 交易统计
        self.stats = {
            'total_trades': 0,
            'total_volume': 0.0,
            'active_orders': 0
        }
        
        logger.info(f"交易引擎已初始化，手续费率：{fee_rate*100}%")
    
    def add_symbol(self, symbol: str, base_currency: str, quote_currency: str):
        """
        添加交易对
        
        Args:
            symbol: 交易对符号 (如 BTC/USDT)
            base_currency: 基础货币 (如 BTC)
            quote_currency: 报价货币 (如 USDT)
        """
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.order_books[symbol] = OrderBook(symbol=symbol)
            logger.info(f"添加交易对：{symbol} ({base_currency}/{quote_currency})")
    
    def submit_order(self, order: Order) -> Tuple[bool, str]:
        """
        提交订单
        
        Args:
            order: 订单对象
        
        Returns:
            (success, message)
        """
        # 验证订单
        valid, msg = self._validate_order(order)
        if not valid:
            order.status = OrderStatus.REJECTED
            return False, msg
        
        # 检查交易对是否存在
        if order.symbol not in self.symbols:
            return False, f"交易对不存在：{order.symbol}"
        
        # 保存订单
        self.orders[order.order_id] = order
        self.user_orders[order.user_id].append(order.order_id)
        self.stats['active_orders'] += 1
        
        logger.info(f"订单提交：{order.order_id} - {order.side.value} {order.quantity} {order.symbol} @ {order.price}")
        
        # 执行撮合
        trades = self._match_order(order)
        
        if len(trades) > 0:
            logger.info(f"订单成交：{order.order_id} - 成交 {order.filled_quantity}/{order.quantity}")
        
        return True, f"订单已提交：{order.order_id}"
    
    def _validate_order(self, order: Order) -> Tuple[bool, str]:
        """
        验证订单
        
        Returns:
            (valid, message)
        """
        # 检查数量
        if order.quantity <= 0:
            return False, "订单数量必须大于 0"
        
        # 限价单检查价格
        if order.type == OrderType.LIMIT and order.price is None:
            return False, "限价单必须指定价格"
        
        if order.type == OrderType.LIMIT and order.price <= 0:
            return False, "价格必须大于 0"
        
        # 检查用户余额 (简化版，实际应该调用钱包服务)
        # if not self._check_user_balance(order):
        #     return False, "用户余额不足"
        
        return True, "订单验证通过"
    
    def _match_order(self, order: Order) -> List[Trade]:
        """
        撮合订单
        
        Args:
            order: 待撮合订单
        
        Returns:
            成交记录列表
        """
        trades = []
        order_book = self.order_books[order.symbol]
        
        if order.side == OrderSide.BUY:
            # 买单：与卖单撮合
            trades = self._match_buy_order(order, order_book)
        else:
            # 卖单：与买单撮合
            trades = self._match_sell_order(order, order_book)
        
        # 更新订单状态
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIAL_FILLED
        
        order.updated_at = datetime.now()
        
        # 更新统计
        self.stats['total_trades'] += len(trades)
        self.stats['active_orders'] = sum(1 for o in self.orders.values() if o.is_active)
        
        return trades
    
    def _match_buy_order(self, buy_order: Order, order_book: OrderBook) -> List[Trade]:
        """
        撮合买单
        
        原则：价格优先，时间优先
        """
        trades = []
        
        # 按价格升序排序卖单
        order_book.asks.sort(key=lambda x: x[0])
        
        i = 0
        while i < len(order_book.asks) and buy_order.remaining_quantity > 0:
            ask_price, ask_quantity = order_book.asks[i]
            
            # 限价单：买入价必须 >= 卖出价
            if buy_order.type == OrderType.LIMIT and buy_order.price < ask_price:
                break
            
            # 计算成交量
            fill_quantity = min(buy_order.remaining_quantity, ask_quantity)
            
            # 创建成交记录
            trade = self._create_trade(
                symbol=buy_order.symbol,
                buyer_order=buy_order,
                seller_order_id=self._find_order_id_at_price(order_book, ask_price, OrderSide.SELL),
                price=ask_price,
                quantity=fill_quantity
            )
            
            if trade:
                trades.append(trade)
                
                # 更新买单
                buy_order.filled_quantity += fill_quantity
                buy_order.fee += self._calculate_fee(fill_quantity * ask_price)
                
                # 更新卖单
                order_book.asks[i] = (ask_price, ask_quantity - fill_quantity)
                
                logger.info(f"成交：{trade.trade_id} - {fill_quantity} @ {ask_price}")
            
            # 如果卖单完全成交，移除
            if order_book.asks[i][1] <= 0:
                i += 1
        
        return trades
    
    def _match_sell_order(self, sell_order: Order, order_book: OrderBook) -> List[Trade]:
        """
        撮合卖单
        
        原则：价格优先，时间优先
        """
        trades = []
        
        # 按价格降序排序买单
        order_book.bids.sort(key=lambda x: x[0], reverse=True)
        
        i = 0
        while i < len(order_book.bids) and sell_order.remaining_quantity > 0:
            bid_price, bid_quantity = order_book.bids[i]
            
            # 限价单：卖出价必须 <= 买入价
            if sell_order.type == OrderType.LIMIT and sell_order.price > bid_price:
                break
            
            # 计算成交量
            fill_quantity = min(sell_order.remaining_quantity, bid_quantity)
            
            # 创建成交记录
            trade = self._create_trade(
                symbol=sell_order.symbol,
                buyer_order_id=self._find_order_id_at_price(order_book, bid_price, OrderSide.BUY),
                seller_order=sell_order,
                price=bid_price,
                quantity=fill_quantity
            )
            
            if trade:
                trades.append(trade)
                
                # 更新卖单
                sell_order.filled_quantity += fill_quantity
                sell_order.fee += self._calculate_fee(fill_quantity * bid_price)
                
                # 更新买单
                order_book.bids[i] = (bid_price, bid_quantity - fill_quantity)
                
                logger.info(f"成交：{trade.trade_id} - {fill_quantity} @ {bid_price}")
            
            # 如果买单完全成交，移除
            if order_book.bids[i][1] <= 0:
                i += 1
        
        return trades
    
    def _create_trade(self, symbol: str, buyer_order: Order = None, seller_order: Order = None,
                      buyer_order_id: str = None, seller_order_id: str = None,
                      price: float = 0.0, quantity: float = 0.0) -> Optional[Trade]:
        """
        创建成交记录
        
        Args:
            symbol: 交易对
            buyer_order: 买方订单
            seller_order: 卖方订单
            buyer_order_id: 买方订单 ID
            seller_order_id: 卖方订单 ID
            price: 成交价格
            quantity: 成交数量
        
        Returns:
            Trade 对象
        """
        try:
            # 获取订单信息
            if buyer_order:
                buyer_order_id = buyer_order.order_id
                buyer_user_id = buyer_order.user_id
            elif buyer_order_id and buyer_order_id in self.orders:
                buyer_user_id = self.orders[buyer_order_id].user_id
            else:
                return None
            
            if seller_order:
                seller_order_id = seller_order.order_id
                seller_user_id = seller_order.user_id
            elif seller_order_id and seller_order_id in self.orders:
                seller_user_id = self.orders[seller_order_id].user_id
            else:
                return None
            
            # 计算手续费 (向买方收取)
            fee = self._calculate_fee(price * quantity)
            
            trade = Trade(
                trade_id=None,
                symbol=symbol,
                buyer_order_id=buyer_order_id,
                seller_order_id=seller_order_id,
                buyer_user_id=buyer_user_id,
                seller_user_id=seller_user_id,
                price=price,
                quantity=quantity,
                fee=fee,
                fee_currency="USDT"
            )
            
            self.trades.append(trade)
            return trade
            
        except Exception as e:
            logger.error(f"创建成交记录失败：{e}")
            return None
    
    def _find_order_id_at_price_and_side(self, order_book: OrderBook, price: float, side: OrderSide) -> str:
        """根据价格和方向查找订单 ID"""
        # 简化实现，实际应该维护价格到订单 ID 的映射
        if side == OrderSide.BUY:
            for i, (p, q) in enumerate(order_book.bids):
                if p == price and q > 0:
                    return f"bid_{price}_{i}"
        else:
            for i, (p, q) in enumerate(order_book.asks):
                if p == price and q > 0:
                    return f"ask_{price}_{i}"
        return f"order_{price}_{side.value}"
    
    def _add_to_order_book(self, order: Order):
        """
        将订单添加到订单簿
        
        Args:
            order: 订单对象
        """
        if order.symbol not in self.order_books:
            return
        
        order_book = self.order_books[order.symbol]
        remaining = order.remaining_quantity
        
        if order.side == OrderSide.BUY:
            # 添加到买单
            order_book.bids.append((order.price, remaining))
            logger.debug(f"买单添加到订单簿：{order.price} x {remaining}")
        else:
            # 添加到卖单
            order_book.asks.append((order.price, remaining))
            logger.debug(f"卖单添加到订单簿：{order.price} x {remaining}")
    
    def _calculate_fee(self, amount: float) -> float:
        """
        计算手续费
        
        Args:
            amount: 交易金额
        
        Returns:
            手续费
        """
        return amount * self.fee_rate
    
    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
        
        Returns:
            (success, message)
        """
        if order_id not in self.orders:
            return False, f"订单不存在：{order_id}"
        
        order = self.orders[order_id]
        
        if not order.is_active:
            return False, f"订单已 {order.status.value}，无法取消"
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        self.stats['active_orders'] -= 1
        
        logger.info(f"订单已取消：{order_id}")
        
        return True, "订单已取消"
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单详情"""
        return self.orders.get(order_id)
    
    def get_order_book(self, symbol: str, depth: int = 10) -> Dict:
        """
        获取订单簿
        
        Args:
            symbol: 交易对
            depth: 深度
        
        Returns:
            订单簿数据
        """
        if symbol not in self.order_books:
            return {"error": "交易对不存在"}
        
        order_book = self.order_books[symbol]
        
        # 排序并截取
        bids = sorted(order_book.bids, key=lambda x: x[0], reverse=True)[:depth]
        asks = sorted(order_book.asks, key=lambda x: x[0])[:depth]
        
        return {
            "symbol": symbol,
            "bids": [{"price": p, "quantity": q} for p, q in bids],
            "asks": [{"price": p, "quantity": q} for p, q in asks],
            "best_bid": order_book.get_best_bid(),
            "best_ask": order_book.get_best_ask(),
            "spread": order_book.get_spread(),
            "mid_price": order_book.get_mid_price(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        获取行情信息
        
        Args:
            symbol: 交易对
        
        Returns:
            行情数据
        """
        order_book = self.order_books.get(symbol)
        if not order_book:
            return {"error": "交易对不存在"}
        
        # 计算 24 小时统计 (简化版)
        recent_trades = [t for t in self.trades if t.symbol == symbol][-100:]
        
        if recent_trades:
            high = max(t.price for t in recent_trades)
            low = min(t.price for t in recent_trades)
            last = recent_trades[-1].price
            volume = sum(t.quantity for t in recent_trades)
        else:
            high = low = last = volume = 0.0
        
        return {
            "symbol": symbol,
            "last": last,
            "high_24h": high,
            "low_24h": low,
            "volume_24h": volume,
            "best_bid": order_book.get_best_bid(),
            "best_ask": order_book.get_best_ask(),
            "spread": order_book.get_spread(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_user_orders(self, user_id: str, status: Optional[OrderStatus] = None) -> List[Order]:
        """
        获取用户订单
        
        Args:
            user_id: 用户 ID
            status: 订单状态过滤
        
        Returns:
            订单列表
        """
        order_ids = self.user_orders.get(user_id, [])
        orders = [self.orders[oid] for oid in order_ids if oid in self.orders]
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        return orders
    
    def get_stats(self) -> Dict:
        """获取交易统计"""
        return {
            **self.stats,
            "symbols_count": len(self.symbols),
            "orders_count": len(self.orders),
            "trades_count": len(self.trades),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """测试主函数"""
    print("=" * 60)
    print("🚀 GlobalTokenHub - 交易引擎测试")
    print("=" * 60)
    
    # 创建交易引擎
    engine = TradingEngine(fee_rate=0.001)  # 0.1% 手续费
    
    # 添加交易对
    engine.add_symbol("BTC/USDT", "BTC", "USDT")
    engine.add_symbol("ETH/USDT", "ETH", "USDT")
    
    print("\n✅ 交易引擎初始化完成")
    print(f"交易对：{engine.symbols}")
    
    # 测试订单
    print("\n📋 测试订单提交...")
    
    # 卖单
    sell_order = Order(
        order_id=None,
        user_id="user_001",
        symbol="BTC/USDT",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        price=50000.0,
        quantity=0.1
    )
    
    success, msg = engine.submit_order(sell_order)
    print(f"卖单提交：{'✅' if success else '❌'} - {msg}")
    
    # 买单
    buy_order = Order(
        order_id=None,
        user_id="user_002",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        price=50000.0,
        quantity=0.05
    )
    
    success, msg = engine.submit_order(buy_order)
    print(f"买单提交：{'✅' if success else '❌'} - {msg}")
    
    # 获取订单簿
    print("\n📊 订单簿:")
    order_book = engine.get_order_book("BTC/USDT")
    best_bid = order_book.get('best_bid')
    best_ask = order_book.get('best_ask')
    spread = order_book.get('spread')
    print(f"  最高买价：${best_bid:,.2f}" if best_bid else "  最高买价：无")
    print(f"  最低卖价：${best_ask:,.2f}" if best_ask else "  最低卖价：无")
    print(f"  价差：${spread:,.2f}" if spread else "  价差：无")
    
    # 获取行情
    print("\n💹 行情信息:")
    ticker = engine.get_ticker("BTC/USDT")
    print(f"  最新价：${ticker.get('last', 0):,.2f}")
    print(f"  24h 最高：${ticker.get('high_24h', 0):,.2f}")
    print(f"  24h 最低：${ticker.get('low_24h', 0):,.2f}")
    print(f"  24h 成交量：{ticker.get('volume_24h', 0):,.4f} BTC")
    
    # 交易统计
    print("\n📈 交易统计:")
    stats = engine.get_stats()
    print(f"  总成交数：{stats['total_trades']}")
    print(f"  活跃订单：{stats['active_orders']}")
    print(f"  交易对数量：{stats['symbols_count']}")
    
    print("\n" + "=" * 60)
    print("✅ 交易引擎测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
