"""
券商基础接口
定义所有券商必须实现的接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"           # 待提交
    SUBMITTED = "submitted"       # 已提交
    PARTIAL = "partial"           # 部分成交
    FILLED = "filled"             # 完全成交
    CANCELLED = "cancelled"       # 已撤销
    REJECTED = "rejected"         # 已拒绝
    FAILED = "failed"             # 失败


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"             # 市价单
    LIMIT = "limit"               # 限价单
    STOP = "stop"                 # 止损单
    STOP_LIMIT = "stop_limit"     # 止损限价单


class TradeDirection(Enum):
    """交易方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderResult:
    """订单结果"""
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    filled_volume: int = 0
    filled_price: float = 0.0
    commission: float = 0.0
    timestamp: datetime = None
    
    def to_dict(self):
        return {
            "success": self.success,
            "order_id": self.order_id,
            "message": self.message,
            "filled_volume": self.filled_volume,
            "filled_price": self.filled_price,
            "commission": self.commission,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class AccountInfo:
    """账户信息"""
    balance: float                    # 可用资金
    frozen: float = 0.0              # 冻结资金
    market_value: float = 0.0        # 持仓市值
    total_asset: float = 0.0         # 总资产
    available_margin: float = 0.0    # 可用保证金
    margin_used: float = 0.0         # 已用保证金
    
    def to_dict(self):
        return {
            "balance": self.balance,
            "frozen": self.frozen,
            "market_value": self.market_value,
            "total_asset": self.total_asset,
            "available_margin": self.available_margin,
            "margin_used": self.margin_used
        }


@dataclass
class PositionInfo:
    """持仓信息"""
    stock_code: str                  # 股票代码
    stock_name: str                  # 股票名称
    volume: int                      # 持仓数量
    available_volume: int            # 可用数量
    cost_price: float                # 成本价
    current_price: float             # 当前价
    market_value: float              # 市值
    profit: float                    # 盈亏金额
    profit_percent: float            # 盈亏百分比
    today_volume: int = 0            # 今日买入量
    
    def to_dict(self):
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "volume": self.volume,
            "available_volume": self.available_volume,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "profit": self.profit,
            "profit_percent": self.profit_percent,
            "today_volume": self.today_volume
        }


@dataclass
class OrderInfo:
    """订单信息"""
    order_id: str                    # 订单ID
    stock_code: str                  # 股票代码
    stock_name: str                  # 股票名称
    direction: TradeDirection        # 方向
    order_type: OrderType            # 类型
    price: float                     # 价格
    volume: int                      # 数量
    filled_volume: int = 0           # 成交数量
    filled_price: float = 0.0        # 成交均价
    status: OrderStatus = OrderStatus.PENDING
    message: str = ""                # 状态消息
    created_at: datetime = None       # 创建时间
    updated_at: datetime = None       # 更新时间
    
    def to_dict(self):
        return {
            "order_id": self.order_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "direction": self.direction.value,
            "order_type": self.order_type.value,
            "price": self.price,
            "volume": self.volume,
            "filled_volume": self.filled_volume,
            "filled_price": self.filled_price,
            "status": self.status.value,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class QuoteInfo:
    """行情信息"""
    stock_code: str                  # 股票代码
    stock_name: str                  # 股票名称
    price: float                     # 当前价
    open: float                      # 开盘价
    high: float                      # 最高价
    low: float                       # 最低价
    pre_close: float                 # 昨收
    volume: int                       # 成交量
    amount: float                    # 成交额
    bid_price: float = 0.0           # 买一价
    ask_price: float = 0.0           # 卖一价
    bid_volume: int = 0              # 买一量
    ask_volume: int = 0              # 卖一量
    timestamp: datetime = None       # 时间戳
    
    def to_dict(self):
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "price": self.price,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "pre_close": self.pre_close,
            "volume": self.volume,
            "amount": self.amount,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class BrokerBase(ABC):
    """
    券商基础类
    所有券商接口必须继承此类并实现所有抽象方法
    """
    
    # 券商标识
    BROKER_ID: str = "base"
    BROKER_NAME: str = "基础券商"
    SUPPORTS_MARGIN: bool = False   # 是否支持融资融券
    SUPPORTS_SHORT: bool = False    # 是否支持做空
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化券商接口
        
        Args:
            config: 券商配置，包含账号密码等
        """
        self.config = config or {}
        self._connected = False
        self._account_id = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        连接券商服务器
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        断开连接
        
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """
        检查连接状态
        
        Returns:
            bool: 是否已连接
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """
        获取账户信息
        
        Returns:
            AccountInfo: 账户信息
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[PositionInfo]:
        """
        获取持仓列表
        
        Returns:
            List[PositionInfo]: 持仓列表
        """
        pass
    
    @abstractmethod
    async def get_orders(self, status: OrderStatus = None, limit: int = 50) -> List[OrderInfo]:
        """
        获取订单列表
        
        Args:
            status: 订单状态筛选
            limit: 返回数量限制
            
        Returns:
            List[OrderInfo]: 订单列表
        """
        pass
    
    @abstractmethod
    async def place_order(
        self,
        stock_code: str,
        direction: TradeDirection,
        volume: int,
        price: float = None,
        order_type: OrderType = OrderType.LIMIT
    ) -> OrderResult:
        """
        下单
        
        Args:
            stock_code: 股票代码
            direction: 方向 (buy/sell)
            volume: 数量 (必须为100的整数倍)
            price: 价格 (市价单可不传)
            order_type: 订单类型
            
        Returns:
            OrderResult: 下单结果
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 撤单是否成功
        """
        pass
    
    @abstractmethod
    async def get_quote(self, stock_code: str) -> QuoteInfo:
        """
        获取实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            QuoteInfo: 行情信息
        """
        pass
    
    @abstractmethod
    async def get_quotes(self, stock_codes: List[str]) -> List[QuoteInfo]:
        """
        批量获取行情
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            List[QuoteInfo]: 行情列表
        """
        pass
    
    @abstractmethod
    async def subscribe_quotes(self, stock_codes: List[str], callback):
        """
        订阅实时行情推送
        
        Args:
            stock_codes: 股票代码列表
            callback: 回调函数
        """
        pass
    
    @abstractmethod
    async def unsubscribe_quotes(self, stock_codes: List[str]):
        """
        取消订阅
        
        Args:
            stock_codes: 股票代码列表
        """
        pass
    
    # ============ 辅助方法 ============
    
    def validate_stock_code(self, stock_code: str) -> bool:
        """验证股票代码格式"""
        # A股: 6位数字
        if len(stock_code) != 6:
            return False
        if not stock_code.isdigit():
            return False
        # 检查市场
        if stock_code.startswith('6'):
            return True  # 上海
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            return True  # 深圳
        elif stock_code.startswith('68'):
            return True  # 科创板
        elif stock_code.startswith('8') or stock_code.startswith('4'):
            return True  # 北交所
        return False
    
    def validate_volume(self, volume: int) -> bool:
        """验证数量是否为100的整数倍"""
        return volume > 0 and volume % 100 == 0
    
    def calculate_commission(self, amount: float, is_sell: bool = False) -> float:
        """
        计算手续费
        
        Args:
            amount: 成交金额
            is_sell: 是否卖出
            
        Returns:
            float: 手续费金额
        """
        # 默认费率，子类可覆盖
        commission_rate = 0.00025  # 万分之2.5
        stamp_duty_rate = 0.001    # 千分之一印花税（仅卖出）
        transfer_fee_rate = 0.00001  # 过户费万分之一
        
        commission = amount * commission_rate
        # 最低5元
        if commission < 5:
            commission = 5
        
        if is_sell:
            commission += amount * stamp_duty_rate
        
        commission += amount * transfer_fee_rate
        
        return round(commission, 2)