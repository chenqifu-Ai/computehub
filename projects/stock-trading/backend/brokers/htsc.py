"""
华泰证券 (htsc) 实盘接口
需要安装: pip install htsc

配置示例:
{
    "account": "账户号",
    "password": "密码",
    "client_path": "华泰客户端路径 (可选)"
}
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import (
    BrokerBase, OrderResult, AccountInfo, PositionInfo,
    OrderInfo, OrderStatus, OrderType, TradeDirection, QuoteInfo
)


class HTSCBroker(BrokerBase):
    """
    华泰证券接口
    通过 htsc 库实现实盘交易
    
    安装: pip install htsc
    
    注意:
    - 需要在华泰开通程序化交易权限
    - 支持融资融券
    """
    
    BROKER_ID = "htsc"
    BROKER_NAME = "华泰证券"
    SUPPORTS_MARGIN = True
    SUPPORTS_SHORT = True
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        self._account = config.get("account", "") if config else ""
        self._password = config.get("password", "") if config else ""
        self._client_path = config.get("client_path", "") if config else ""
        
        self._client = None
    
    async def connect(self) -> bool:
        """连接"""
        try:
            # 导入 htsc
            # import htsc
            # self._client = htsc.HtscClient()
            # result = self._client.login(self._account, self._password)
            
            # TODO: 实现实际登录逻辑
            self._connected = True
            return True
            
        except ImportError:
            print("请安装 htsc: pip install htsc")
            self._connected = False
            return False
        except Exception as e:
            print(f"连接失败: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> bool:
        """断开"""
        if self._client:
            # self._client.logout()
            pass
        self._connected = False
        return True
    
    async def is_connected(self) -> bool:
        """检查连接"""
        return self._connected
    
    async def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        # TODO: 实现
        return AccountInfo(balance=0)
    
    async def get_positions(self) -> List[PositionInfo]:
        """获取持仓"""
        # TODO: 实现
        return []
    
    async def get_orders(self, status: OrderStatus = None, limit: int = 50) -> List[OrderInfo]:
        """获取订单"""
        # TODO: 实现
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
        # TODO: 实现
        return OrderResult(success=False, message="未实现")
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        # TODO: 实现
        return False
    
    async def get_quote(self, stock_code: str) -> Optional[QuoteInfo]:
        """获取行情"""
        # TODO: 实现
        return None
    
    async def get_quotes(self, stock_codes: List[str]) -> List[QuoteInfo]:
        """批量获取行情"""
        # TODO: 实现
        return []
    
    async def subscribe_quotes(self, stock_codes: List[str], callback):
        """订阅行情"""
        pass
    
    async def unsubscribe_quotes(self, stock_codes: List[str]):
        """取消订阅"""
        pass