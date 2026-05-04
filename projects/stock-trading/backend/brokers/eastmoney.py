"""
东方财富实盘接口
需要安装: pip install efinance

配置示例:
{
    "account": "账户号",
    "password": "密码",
    "trade_server": "交易服务器地址",
    "hq_server": "行情服务器地址"
}
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import (
    BrokerBase, OrderResult, AccountInfo, PositionInfo,
    OrderInfo, OrderStatus, OrderType, TradeDirection, QuoteInfo
)


class EastMoneyBroker(BrokerBase):
    """
    东方财富券商接口
    通过 efinance 库实现实盘交易
    
    安装: pip install efinance
    
    支持功能:
    - 登录验证
    - 账户查询
    - 持仓查询
    - 下单/撤单
    - 实时行情
    """
    
    BROKER_ID = "eastmoney"
    BROKER_NAME = "东方财富"
    SUPPORTS_MARGIN = True
    SUPPORTS_SHORT = False
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # 券商配置
        self._account = config.get("account", "") if config else ""
        self._password = config.get("password", "") if config else ""
        self._trade_server = config.get("trade_server", "") if config else ""
        self._hq_server = config.get("hq_server", "") if config else ""
        
        # efinance 实例
        self._client = None
    
    async def connect(self) -> bool:
        """连接券商服务器"""
        try:
            import efinance as ef
            
            # 登录
            self._client = ef.EastMoneyClient()
            
            # 验证登录
            if self._account and self._password:
                result = self._client.login(
                    account=self._account,
                    password=self._password,
                    trade_server=self._trade_server,
                    hq_server=self._hq_server
                )
                if result.get('success'):
                    self._connected = True
                    self._account_id = self._account
                    return True
                else:
                    self._connected = False
                    return False
            
            # 未配置账号时，使用模拟模式
            self._connected = True
            return True
            
        except ImportError:
            print("请安装 efinance: pip install efinance")
            self._connected = False
            return False
        except Exception as e:
            print(f"连接失败: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> bool:
        """断开连接"""
        if self._client:
            try:
                self._client.logout()
            except:
                pass
        
        self._connected = False
        self._client = None
        return True
    
    async def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    async def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        if not self._connected or not self._client:
            return AccountInfo(balance=0)
        
        try:
            # 获取资金账号信息
            fund_info = self._client.get_fund_info()
            
            return AccountInfo(
                balance=float(fund_info.get('可用资金', 0)),
                frozen=float(fund_info.get('冻结资金', 0)),
                market_value=float(fund_info.get('持仓市值', 0)),
                total_asset=float(fund_info.get('总资产', 0)),
                available_margin=float(fund_info.get('可用保证金', 0)) if '可用保证金' in fund_info else 0,
                margin_used=float(fund_info.get('已用保证金', 0)) if '已用保证金' in fund_info else 0
            )
        except Exception as e:
            print(f"获取账户信息失败: {e}")
            return AccountInfo(balance=0)
    
    async def get_positions(self) -> List[PositionInfo]:
        """获取持仓"""
        if not self._connected or not self._client:
            return []
        
        try:
            positions = self._client.get_positions()
            
            result = []
            for pos in positions:
                result.append(PositionInfo(
                    stock_code=pos.get('股票代码', ''),
                    stock_name=pos.get('股票名称', ''),
                    volume=int(pos.get('持仓数量', 0)),
                    available_volume=int(pos.get('可用数量', 0)),
                    cost_price=float(pos.get('成本价', 0)),
                    current_price=float(pos.get('当前价', 0)),
                    market_value=float(pos.get('市值', 0)),
                    profit=float(pos.get('盈亏', 0)),
                    profit_percent=float(pos.get('盈亏比例', 0))
                ))
            
            return result
        except Exception as e:
            print(f"获取持仓失败: {e}")
            return []
    
    async def get_orders(self, status: OrderStatus = None, limit: int = 50) -> List[OrderInfo]:
        """获取订单"""
        if not self._connected or not self._client:
            return []
        
        try:
            orders = self._client.get_orders()
            
            result = []
            for order in orders:
                # 映射订单状态
                status_map = {
                    '未报': OrderStatus.PENDING,
                    '已报': OrderStatus.SUBMITTED,
                    '部成': OrderStatus.PARTIAL,
                    '已成': OrderStatus.FILLED,
                    '已撤': OrderStatus.CANCELLED,
                    '废单': OrderStatus.REJECTED,
                }
                
                order_status = status_map.get(order.get('状态', ''), OrderStatus.PENDING)
                
                # 状态筛选
                if status and order_status != status:
                    continue
                
                result.append(OrderInfo(
                    order_id=order.get('委托编号', ''),
                    stock_code=order.get('股票代码', ''),
                    stock_name=order.get('股票名称', ''),
                    direction=TradeDirection.BUY if order.get('操作') == '买入' else TradeDirection.SELL,
                    order_type=OrderType.LIMIT if order.get('委托价格') else OrderType.MARKET,
                    price=float(order.get('委托价格', 0)),
                    volume=int(order.get('委托数量', 0)),
                    filled_volume=int(order.get('成交数量', 0)),
                    filled_price=float(order.get('成交均价', 0)),
                    status=order_status,
                    message=order.get('状态说明', ''),
                    created_at=datetime.now(),  # TODO: 解析实际时间
                    updated_at=datetime.now()
                ))
            
            return result[:limit]
        except Exception as e:
            print(f"获取订单失败: {e}")
            return []
    
    async def place_order(
        self,
        stock_code: str,
        direction: TradeDirection,
        volume: int,
        price: float = None,
        order_type: OrderType = OrderType.LIMIT
    ) -> OrderResult:
        """下单"""
        if not self._connected or not self._client:
            return OrderResult(success=False, message="未连接券商")
        
        # 验证
        if not self.validate_stock_code(stock_code):
            return OrderResult(success=False, message=f"无效股票代码: {stock_code}")
        
        if not self.validate_volume(volume):
            return OrderResult(success=False, message=f"数量必须是100的整数倍: {volume}")
        
        try:
            # 下单
            result = self._client.place_order(
                code=stock_code,
                price=price or 0,
                volume=volume,
                direction='buy' if direction == TradeDirection.BUY else 'sell',
                order_type='limit' if order_type == OrderType.LIMIT else 'market'
            )
            
            if result.get('success'):
                return OrderResult(
                    success=True,
                    order_id=result.get('order_id'),
                    message="委托成功",
                    timestamp=datetime.now()
                )
            else:
                return OrderResult(
                    success=False,
                    message=result.get('message', '下单失败')
                )
        except Exception as e:
            return OrderResult(success=False, message=f"下单异常: {e}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if not self._connected or not self._client:
            return False
        
        try:
            result = self._client.cancel_order(order_id)
            return result.get('success', False)
        except Exception as e:
            print(f"撤单失败: {e}")
            return False
    
    async def get_quote(self, stock_code: str) -> Optional[QuoteInfo]:
        """获取实时行情"""
        try:
            import efinance as ef
            
            # 使用 efinance 获取行情
            quote_data = ef.stock.get_quote(stock_code)
            
            if quote_data is None or len(quote_data) == 0:
                return None
            
            q = quote_data.iloc[0] if hasattr(quote_data, 'iloc') else quote_data
            
            return QuoteInfo(
                stock_code=stock_code,
                stock_name=q.get('名称', stock_code),
                price=float(q.get('最新价', 0)),
                open=float(q.get('今开', 0)),
                high=float(q.get('最高', 0)),
                low=float(q.get('最低', 0)),
                pre_close=float(q.get('昨收', 0)),
                volume=int(q.get('成交量', 0)),
                amount=float(q.get('成交额', 0)),
                bid_price=float(q.get('买一价', 0)),
                ask_price=float(q.get('卖一价', 0)),
                bid_volume=int(q.get('买一量', 0)),
                ask_volume=int(q.get('卖一量', 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"获取行情失败: {e}")
            return None
    
    async def get_quotes(self, stock_codes: List[str]) -> List[QuoteInfo]:
        """批量获取行情"""
        try:
            import efinance as ef
            
            quotes_data = ef.stock.get_quotes(stock_codes)
            
            result = []
            for _, q in quotes_data.iterrows():
                result.append(QuoteInfo(
                    stock_code=q.get('代码', ''),
                    stock_name=q.get('名称', ''),
                    price=float(q.get('最新价', 0)),
                    open=float(q.get('今开', 0)),
                    high=float(q.get('最高', 0)),
                    low=float(q.get('最低', 0)),
                    pre_close=float(q.get('昨收', 0)),
                    volume=int(q.get('成交量', 0)),
                    amount=float(q.get('成交额', 0)),
                    timestamp=datetime.now()
                ))
            
            return result
        except Exception as e:
            print(f"批量获取行情失败: {e}")
            return []
    
    async def subscribe_quotes(self, stock_codes: List[str], callback):
        """订阅实时行情"""
        # TODO: 实现WebSocket订阅
        pass
    
    async def unsubscribe_quotes(self, stock_codes: List[str]):
        """取消订阅"""
        pass