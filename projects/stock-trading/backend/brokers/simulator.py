"""
模拟券商
用于开发和测试的模拟交易接口
"""

import json
import time
import uuid
import random
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import URLError

from .base import (
    BrokerBase, OrderResult, AccountInfo, PositionInfo, 
    OrderInfo, OrderStatus, OrderType, TradeDirection, QuoteInfo
)


class SimulatorBroker(BrokerBase):
    """
    模拟券商实现
    - 模拟账户资金和持仓
    - 使用真实行情数据
    - 模拟撮合成交
    """
    
    BROKER_ID = "simulator"
    BROKER_NAME = "模拟交易"
    
    # 模拟账户默认资金
    DEFAULT_BALANCE = 1000000.0  # 100万
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # 模拟账户数据
        self._balance = config.get("initial_balance", self.DEFAULT_BALANCE) if config else self.DEFAULT_BALANCE
        self._frozen = 0.0
        self._positions: Dict[str, PositionInfo] = {}
        self._orders: Dict[str, OrderInfo] = {}
        
        # 行情缓存
        self._quote_cache: Dict[str, tuple] = {}  # (quote, timestamp)
        self._cache_ttl = 5  # 5秒缓存
        
        # 撮合设置
        self._slippage = config.get("slippage", 0.001) if config else 0.001  # 滑点 0.1%
        self._commission_rate = config.get("commission_rate", 0.00025) if config else 0.00025
    
    async def connect(self) -> bool:
        """连接（模拟）"""
        self._connected = True
        return True
    
    async def disconnect(self) -> bool:
        """断开连接"""
        self._connected = False
        return True
    
    async def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    async def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        # 计算市值
        market_value = sum(
            pos.current_price * pos.volume 
            for pos in self._positions.values()
        )
        
        # 计算总资产
        total_asset = self._balance + market_value
        
        return AccountInfo(
            balance=self._balance,
            frozen=self._frozen,
            market_value=round(market_value, 2),
            total_asset=round(total_asset, 2),
            available_margin=0,  # 模拟盘不支持融资
            margin_used=0
        )
    
    async def get_positions(self) -> List[PositionInfo]:
        """获取持仓"""
        # 更新实时价格
        for pos in self._positions.values():
            quote = await self.get_quote(pos.stock_code)
            if quote:
                pos.current_price = quote.price
                pos.market_value = round(quote.price * pos.volume, 2)
                pos.profit = round((quote.price - pos.cost_price) * pos.volume, 2)
                pos.profit_percent = round(
                    (quote.price / pos.cost_price - 1) * 100, 2
                ) if pos.cost_price > 0 else 0
        
        return list(self._positions.values())
    
    async def get_orders(self, status: OrderStatus = None, limit: int = 50) -> List[OrderInfo]:
        """获取订单"""
        orders = list(self._orders.values())
        
        # 按状态筛选
        if status:
            orders = [o for o in orders if o.status == status]
        
        # 按时间倒序
        orders.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        
        return orders[:limit]
    
    async def place_order(
        self,
        stock_code: str,
        direction: TradeDirection,
        volume: int,
        price: float = None,
        order_type: OrderType = OrderType.LIMIT
    ) -> OrderResult:
        """下单"""
        if not self._connected:
            return OrderResult(
                success=False,
                message="未连接券商服务器"
            )
        
        # 验证股票代码
        if not self.validate_stock_code(stock_code):
            return OrderResult(
                success=False,
                message=f"无效的股票代码: {stock_code}"
            )
        
        # 验证数量
        if not self.validate_volume(volume):
            return OrderResult(
                success=False,
                message=f"买入数量必须是100的整数倍，当前: {volume}"
            )
        
        # 获取行情
        quote = await self.get_quote(stock_code)
        if not quote:
            return OrderResult(
                success=False,
                message=f"无法获取股票行情: {stock_code}"
            )
        
        # 确定价格
        if order_type == OrderType.MARKET:
            # 市价单使用买一/卖一价
            if direction == TradeDirection.BUY:
                price = quote.ask_price if quote.ask_price > 0 else quote.price
            else:
                price = quote.bid_price if quote.bid_price > 0 else quote.price
        elif price is None:
            price = quote.price
        
        # 加入滑点
        actual_price = price * (1 + random.uniform(-self._slippage, self._slippage))
        
        # 计算金额和手续费
        amount = actual_price * volume
        commission = self.calculate_commission(amount, direction == TradeDirection.SELL)
        
        # 生成订单ID
        order_id = f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}"
        
        # 买入检查
        total_cost = amount + commission
        if direction == TradeDirection.BUY:
            if total_cost > self._balance:
                return OrderResult(
                    success=False,
                    message=f"资金不足，需要 {total_cost:.2f}，可用 {self._balance:.2f}"
                )
        
        # 卖出检查
        if direction == TradeDirection.SELL:
            if stock_code not in self._positions:
                return OrderResult(
                    success=False,
                    message=f"没有该股票持仓: {stock_code}"
                )
            pos = self._positions[stock_code]
            if volume > pos.available_volume:
                return OrderResult(
                    success=False,
                    message=f"可卖数量不足，需要 {volume}，可用 {pos.available_volume}"
                )
        
        # 执行交易
        if direction == TradeDirection.BUY:
            # 扣除资金
            self._balance -= total_cost
            
            # 更新持仓
            if stock_code in self._positions:
                pos = self._positions[stock_code]
                total_cost = pos.cost_price * pos.volume + amount
                total_volume = pos.volume + volume
                pos.cost_price = total_cost / total_volume
                pos.volume = total_volume
                pos.available_volume = total_volume  # T+0模拟
            else:
                self._positions[stock_code] = PositionInfo(
                    stock_code=stock_code,
                    stock_name=quote.stock_name,
                    volume=volume,
                    available_volume=volume,
                    cost_price=actual_price,
                    current_price=actual_price,
                    market_value=amount,
                    profit=0,
                    profit_percent=0
                )
        else:
            # 卖出
            pos = self._positions[stock_code]
            pos.volume -= volume
            pos.available_volume -= volume
            
            # 增加资金
            self._balance += amount - commission
            
            # 清空持仓
            if pos.volume == 0:
                del self._positions[stock_code]
        
        # 创建订单记录
        order = OrderInfo(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=quote.stock_name,
            direction=direction,
            order_type=order_type,
            price=price,
            volume=volume,
            filled_volume=volume,
            filled_price=actual_price,
            status=OrderStatus.FILLED,
            message="成交",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self._orders[order_id] = order
        
        return OrderResult(
            success=True,
            order_id=order_id,
            message="委托成功",
            filled_volume=volume,
            filled_price=actual_price,
            commission=commission,
            timestamp=datetime.now()
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤单（模拟盘订单立即成交，无法撤单）"""
        if order_id not in self._orders:
            return False
        
        order = self._orders[order_id]
        if order.status == OrderStatus.FILLED:
            return False  # 已成交无法撤销
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        return True
    
    async def get_quote(self, stock_code: str) -> Optional[QuoteInfo]:
        """获取实时行情（从腾讯API获取）"""
        # 检查缓存
        cache_key = f"quote_{stock_code}"
        if cache_key in self._quote_cache:
            cached, ts = self._quote_cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                return cached
        
        # 从腾讯API获取
        quote = await self._fetch_quote_tencent(stock_code)
        
        if quote:
            self._quote_cache[cache_key] = (quote, time.time())
        
        return quote
    
    async def get_quotes(self, stock_codes: List[str]) -> List[QuoteInfo]:
        """批量获取行情"""
        quotes = []
        for code in stock_codes:
            quote = await self.get_quote(code)
            if quote:
                quotes.append(quote)
        return quotes
    
    async def subscribe_quotes(self, stock_codes: List[str], callback):
        """订阅行情（模拟盘暂不支持）"""
        pass
    
    async def unsubscribe_quotes(self, stock_codes: List[str]):
        """取消订阅"""
        pass
    
    # ============ 内部方法 ============
    
    async def _fetch_quote_tencent(self, stock_code: str) -> Optional[QuoteInfo]:
        """从腾讯API获取行情"""
        # 确定市场前缀
        if stock_code.startswith('6'):
            market_code = f'sh{stock_code}'
        else:
            market_code = f'sz{stock_code}'
        
        try:
            url = f'http://qt.gtimg.cn/q={market_code}'
            req = Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://qt.gtimg.cn/'
            })
            response = urlopen(req, timeout=5)
            data = response.read().decode('gbk')
            
            # 解析数据
            if '~' not in data:
                return None
            
            parts = data.split('~')
            
            return QuoteInfo(
                stock_code=stock_code,
                stock_name=parts[1] if len(parts) > 1 else stock_code,
                price=float(parts[3]) if len(parts) > 3 else 0,
                open=float(parts[5]) if len(parts) > 5 else 0,
                high=float(parts[4]) if len(parts) > 4 else 0,
                low=float(parts[4]) if len(parts) > 4 else 0,
                pre_close=float(parts[4]) if len(parts) > 4 else 0,
                volume=int(float(parts[6])) if len(parts) > 6 else 0,
                amount=float(parts[37]) if len(parts) > 37 else 0,
                bid_price=float(parts[9]) if len(parts) > 9 else 0,
                ask_price=float(parts[18]) if len(parts) > 18 else 0,
                bid_volume=int(float(parts[10])) if len(parts) > 10 else 0,
                ask_volume=int(float(parts[20])) if len(parts) > 20 else 0,
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f'获取行情失败 {stock_code}: {e}')
            return None
    
    # ============ 持久化方法 ============
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态"""
        return {
            "balance": self._balance,
            "frozen": self._frozen,
            "positions": {
                code: {
                    "stock_code": pos.stock_code,
                    "stock_name": pos.stock_name,
                    "volume": pos.volume,
                    "available_volume": pos.available_volume,
                    "cost_price": pos.cost_price
                }
                for code, pos in self._positions.items()
            },
            "orders": {
                oid: order.to_dict()
                for oid, order in self._orders.items()
            }
        }
    
    def load_state(self, state: Dict[str, Any]):
        """加载状态"""
        self._balance = state.get("balance", self.DEFAULT_BALANCE)
        self._frozen = state.get("frozen", 0)
        
        # 加载持仓
        for code, pos_data in state.get("positions", {}).items():
            self._positions[code] = PositionInfo(
                stock_code=pos_data["stock_code"],
                stock_name=pos_data["stock_name"],
                volume=pos_data["volume"],
                available_volume=pos_data["available_volume"],
                cost_price=pos_data["cost_price"],
                current_price=pos_data["cost_price"],  # 稍后更新
                market_value=0,
                profit=0,
                profit_percent=0
            )
        
        # 加载订单
        for oid, order_data in state.get("orders", {}).items():
            self._orders[oid] = OrderInfo(
                order_id=order_data["order_id"],
                stock_code=order_data["stock_code"],
                stock_name=order_data["stock_name"],
                direction=TradeDirection(order_data["direction"]),
                order_type=OrderType(order_data["order_type"]),
                price=order_data["price"],
                volume=order_data["volume"],
                filled_volume=order_data["filled_volume"],
                filled_price=order_data["filled_price"],
                status=OrderStatus(order_data["status"]),
                message=order_data.get("message", ""),
                created_at=datetime.fromisoformat(order_data["created_at"]) if order_data.get("created_at") else None,
                updated_at=datetime.fromisoformat(order_data["updated_at"]) if order_data.get("updated_at") else None
            )