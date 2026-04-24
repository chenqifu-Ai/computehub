"""
券商接口模块
支持多家券商的统一接口层
"""

from .base import BrokerBase, OrderResult, AccountInfo, PositionInfo
from .simulator import SimulatorBroker
from .registry import BrokerRegistry

# 可用的券商列表
AVAILABLE_BROKERS = {
    'simulator': SimulatorBroker,
}

# 尝试导入实盘券商
try:
    from .eastmoney import EastMoneyBroker
    AVAILABLE_BROKERS['eastmoney'] = EastMoneyBroker
except ImportError:
    pass

try:
    from .htsc import HTSCBroker  # 华泰证券
    AVAILABLE_BROKERS['htsc'] = HTSCBroker
except ImportError:
    pass

__all__ = [
    'BrokerBase',
    'OrderResult', 
    'AccountInfo',
    'PositionInfo',
    'SimulatorBroker',
    'BrokerRegistry',
    'AVAILABLE_BROKERS'
]