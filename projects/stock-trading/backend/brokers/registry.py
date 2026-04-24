"""
券商注册中心
管理多个券商实例
"""

import os
import json
from typing import Dict, Type, Optional, Any
from pathlib import Path

from .base import BrokerBase
from .simulator import SimulatorBroker


class BrokerRegistry:
    """
    券商注册中心
    
    管理多个券商实例，支持切换和配置
    """
    
    # 已注册的券商类型
    _brokers: Dict[str, Type[BrokerBase]] = {
        'simulator': SimulatorBroker,
    }
    
    # 当前活跃的券商实例
    _instances: Dict[str, BrokerBase] = {}
    
    # 默认券商
    _default_broker: str = 'simulator'
    
    # 配置文件路径
    _config_dir: str = None
    
    @classmethod
    def set_config_dir(cls, config_dir: str):
        """设置配置目录"""
        cls._config_dir = config_dir
    
    @classmethod
    def register(cls, broker_id: str, broker_class: Type[BrokerBase]):
        """
        注册券商类型
        
        Args:
            broker_id: 券商标识
            broker_class: 券商类
        """
        cls._brokers[broker_id] = broker_class
    
    @classmethod
    def get_broker_class(cls, broker_id: str) -> Optional[Type[BrokerBase]]:
        """获取券商类"""
        return cls._brokers.get(broker_id)
    
    @classmethod
    def list_brokers(cls) -> Dict[str, str]:
        """
        列出所有可用券商
        
        Returns:
            Dict[str, str]: {broker_id: broker_name}
        """
        return {
            broker_id: broker_class.BROKER_NAME
            for broker_id, broker_class in cls._brokers.items()
        }
    
    @classmethod
    async def get_instance(
        cls, 
        broker_id: str = None,
        account_id: str = None,
        config: Dict[str, Any] = None
    ) -> BrokerBase:
        """
        获取券商实例
        
        Args:
            broker_id: 券商标识，默认使用default_broker
            account_id: 账户ID，用于区分不同账户
            config: 券商配置
            
        Returns:
            BrokerBase: 券商实例
        """
        if broker_id is None:
            broker_id = cls._default_broker
        
        # 生成实例key
        instance_key = f"{broker_id}:{account_id or 'default'}"
        
        # 检查缓存
        if instance_key in cls._instances:
            return cls._instances[instance_key]
        
        # 创建新实例
        broker_class = cls._brokers.get(broker_id)
        if not broker_class:
            raise ValueError(f"未注册的券商: {broker_id}")
        
        # 合并配置
        final_config = config or {}
        if cls._config_dir:
            # 尝试加载配置文件
            config_file = os.path.join(cls._config_dir, f"{broker_id}.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    final_config = {**file_config, **final_config}
        
        # 创建实例
        instance = broker_class(config=final_config)
        
        # 连接
        await instance.connect()
        
        # 缓存
        cls._instances[instance_key] = instance
        
        return instance
    
    @classmethod
    async def release_instance(cls, broker_id: str, account_id: str = None):
        """
        释放券商实例
        
        Args:
            broker_id: 券商标识
            account_id: 账户ID
        """
        instance_key = f"{broker_id}:{account_id or 'default'}"
        
        if instance_key in cls._instances:
            instance = cls._instances[instance_key]
            await instance.disconnect()
            del cls._instances[instance_key]
    
    @classmethod
    def set_default(cls, broker_id: str):
        """设置默认券商"""
        if broker_id not in cls._brokers:
            raise ValueError(f"未注册的券商: {broker_id}")
        cls._default_broker = broker_id
    
    @classmethod
    def get_default(cls) -> str:
        """获取默认券商"""
        return cls._default_broker
    
    @classmethod
    def load_from_config(cls, config_path: str):
        """
        从配置文件加载券商配置
        
        Args:
            config_path: 配置文件路径
        """
        if not os.path.exists(config_path):
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 设置默认券商
        default_broker = config.get('default_broker')
        if default_broker:
            cls.set_default(default_broker)
        
        # 设置配置目录
        config_dir = os.path.dirname(config_path)
        cls.set_config_dir(config_dir)
    
    @classmethod
    def save_state(cls, broker_id: str, account_id: str = None) -> Dict[str, Any]:
        """
        保存券商状态
        
        Args:
            broker_id: 券商标识
            account_id: 账户ID
            
        Returns:
            Dict: 状态数据
        """
        instance_key = f"{broker_id}:{account_id or 'default'}"
        
        if instance_key not in cls._instances:
            return {}
        
        instance = cls._instances[instance_key]
        
        # 只有模拟盘支持保存状态
        if hasattr(instance, 'save_state'):
            return instance.save_state()
        
        return {}
    
    @classmethod
    def load_state(cls, broker_id: str, state: Dict[str, Any], account_id: str = None):
        """
        加载券商状态
        
        Args:
            broker_id: 券商标识
            state: 状态数据
            account_id: 账户ID
        """
        instance_key = f"{broker_id}:{account_id or 'default'}"
        
        if instance_key not in cls._instances:
            return
        
        instance = cls._instances[instance_key]
        
        if hasattr(instance, 'load_state'):
            instance.load_state(state)


# 尝试导入实盘券商
def _load_real_brokers():
    """加载实盘券商（可选）"""
    try:
        from .eastmoney import EastMoneyBroker
        BrokerRegistry.register('eastmoney', EastMoneyBroker)
    except ImportError:
        pass
    
    try:
        from .htsc import HTSCBroker
        BrokerRegistry.register('htsc', HTSCBroker)
    except ImportError:
        pass
    
    try:
        from .xtquant import XTQuantBroker
        BrokerRegistry.register('xtquant', XTQuantBroker)
    except ImportError:
        pass


# 自动加载
_load_real_brokers()