"""
同步券商包装器
用于 simple_server.py 同步调用
"""

import json
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.request import urlopen, Request
from urllib.error import URLError


class SyncBrokerWrapper:
    """
    同步券商包装器
    提供模拟/实盘交易接口的同步版本
    """
    
    # 券商配置
    DEFAULT_BALANCE = 1000000.0
    
    # 单例实例
    _instance = None
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.current_broker = config.get("default_broker", "simulator") if config else "simulator"
        
        # 模拟账户数据
        self._balance = self.DEFAULT_BALANCE
        self._frozen = 0.0
        self._positions: Dict[str, Dict] = {}
        self._orders: Dict[str, Dict] = {}
        
        # 行情缓存
        self._quote_cache: Dict[str, tuple] = {}
        self._cache_ttl = 5  # 5秒缓存
        
        # 交易设置
        self._slippage = 0.001  # 滑点 0.1%
        self._commission_rate = 0.00025  # 手续费 万分之2.5
    
    @classmethod
    def get_instance(cls):
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def list_brokers(self) -> List[Dict]:
        """列出可用券商"""
        return [
            {"id": "simulator", "name": "模拟交易", "type": "simulator", "enabled": True},
            {"id": "eastmoney", "name": "东方财富", "type": "real", "enabled": False, "note": "需安装 efinance"},
            {"id": "htsc", "name": "华泰证券", "type": "real", "enabled": False, "note": "需开通程序化权限"},
            {"id": "xtquant", "name": "讯投QMT", "type": "real", "enabled": False, "note": "需安装 xtquant"},
        ]
    
    def get_current_broker(self) -> Dict:
        """获取当前券商"""
        brokers = {b["id"]: b for b in self.list_brokers()}
        return {
            "id": self.current_broker,
            "name": brokers.get(self.current_broker, {}).get("name", self.current_broker)
        }
    
    def switch_broker(self, broker_id: str) -> Dict:
        """切换券商"""
        brokers = {b["id"]: b for b in self.list_brokers()}
        
        if broker_id not in brokers:
            return {"success": False, "message": f"不支持的券商: {broker_id}"}
        
        if not brokers[broker_id].get("enabled", True):
            return {"success": False, "message": f"券商 {broker_id} 未启用"}
        
        self.current_broker = broker_id
        return {"success": True, "message": f"已切换到 {brokers[broker_id]['name']}"}
    
    def get_account(self) -> Dict:
        """获取账户信息"""
        # 计算市值
        market_value = 0.0
        for code, pos in self._positions.items():
            quote = self.get_quote(code)
            if quote:
                market_value += quote["price"] * pos["volume"]
        
        total_asset = self._balance + market_value
        profit = total_asset - self.DEFAULT_BALANCE
        
        return {
            "balance": round(self._balance, 2),
            "frozen": round(self._frozen, 2),
            "market_value": round(market_value, 2),
            "total_asset": round(total_asset, 2),
            "profit": round(profit, 2),
            "profit_percent": round(profit / self.DEFAULT_BALANCE * 100, 2) if self.DEFAULT_BALANCE > 0 else 0,
            "initial_capital": self.DEFAULT_BALANCE
        }
    
    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        result = []
        for code, pos in self._positions.items():
            quote = self.get_quote(code)
            if not quote:
                continue
            
            current_price = quote["price"]
            market_value = current_price * pos["volume"]
            profit = (current_price - pos["cost_price"]) * pos["volume"]
            profit_percent = (current_price / pos["cost_price"] - 1) * 100 if pos["cost_price"] > 0 else 0
            
            result.append({
                "stock_code": code,
                "stock_name": pos["name"],
                "volume": pos["volume"],
                "available_volume": pos["volume"],  # T+0 模拟
                "cost_price": round(pos["cost_price"], 2),
                "current_price": round(current_price, 2),
                "market_value": round(market_value, 2),
                "profit": round(profit, 2),
                "profit_percent": round(profit_percent, 2)
            })
        
        return result
    
    def get_orders(self, limit: int = 50) -> List[Dict]:
        """获取订单"""
        orders = list(self._orders.values())
        orders.sort(key=lambda x: x["created_at"], reverse=True)
        return orders[:limit]
    
    def place_order(self, stock_code: str, direction: str, volume: int, price: float = None) -> Dict:
        """下单"""
        # 验证股票代码
        if len(stock_code) != 6 or not stock_code.isdigit():
            return {"success": False, "message": f"无效的股票代码: {stock_code}"}
        
        # 验证数量
        if volume <= 0 or volume % 100 != 0:
            return {"success": False, "message": f"数量必须是100的整数倍: {volume}"}
        
        # 获取行情
        quote = self.get_quote(stock_code)
        if not quote:
            return {"success": False, "message": f"无法获取股票行情: {stock_code}"}
        
        # 确定价格
        if price is None or price <= 0:
            price = quote["price"]
        
        # 加入滑点
        actual_price = price * (1 + random.uniform(-self._slippage, self._slippage))
        
        # 计算金额和手续费
        amount = actual_price * volume
        commission = self.calculate_commission(amount, direction == "sell")
        total_cost = amount + commission
        
        # 生成订单ID
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}"
        
        # 买入检查
        if direction == "buy":
            if total_cost > self._balance:
                return {"success": False, "message": f"资金不足，需要 {total_cost:.2f}，可用 {self._balance:.2f}"}
            
            # 扣除资金
            self._balance -= total_cost
            
            # 更新持仓
            if stock_code in self._positions:
                pos = self._positions[stock_code]
                total_cost_price = pos["cost_price"] * pos["volume"] + amount
                total_volume = pos["volume"] + volume
                pos["cost_price"] = total_cost_price / total_volume
                pos["volume"] = total_volume
            else:
                self._positions[stock_code] = {
                    "name": quote.get("name", stock_code),
                    "volume": volume,
                    "cost_price": actual_price
                }
        else:  # sell
            # 检查持仓
            if stock_code not in self._positions:
                return {"success": False, "message": f"没有该股票持仓: {stock_code}"}
            
            pos = self._positions[stock_code]
            if volume > pos["volume"]:
                return {"success": False, "message": f"可卖数量不足，需要 {volume}，可用 {pos['volume']}"}
            
            # 更新持仓
            pos["volume"] -= volume
            if pos["volume"] == 0:
                del self._positions[stock_code]
            
            # 增加资金
            self._balance += amount - commission
        
        # 创建订单记录
        order = {
            "order_id": order_id,
            "stock_code": stock_code,
            "stock_name": quote.get("name", stock_code),
            "direction": direction,
            "order_type": "limit",
            "price": round(price, 2),
            "volume": volume,
            "filled_volume": volume,
            "filled_price": round(actual_price, 2),
            "status": "filled",
            "message": "成交",
            "commission": round(commission, 2),
            "created_at": datetime.now().isoformat()
        }
        self._orders[order_id] = order
        
        return {
            "success": True,
            "order_id": order_id,
            "message": "委托成功",
            "filled_volume": volume,
            "filled_price": round(actual_price, 2),
            "commission": round(commission, 2)
        }
    
    def cancel_order(self, order_id: str) -> Dict:
        """撤单（模拟盘订单立即成交，无法撤单）"""
        if order_id not in self._orders:
            return {"success": False, "message": "订单不存在"}
        
        order = self._orders[order_id]
        if order["status"] == "filled":
            return {"success": False, "message": "订单已成交，无法撤销"}
        
        order["status"] = "cancelled"
        return {"success": True, "message": "撤单成功"}
    
    def get_quote(self, stock_code: str) -> Optional[Dict]:
        """获取实时行情"""
        # 检查缓存
        cache_key = f"quote_{stock_code}"
        if cache_key in self._quote_cache:
            cached, ts = self._quote_cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                return cached
        
        # 从腾讯API获取
        quote = self._fetch_quote_tencent(stock_code)
        
        if quote:
            self._quote_cache[cache_key] = (quote, time.time())
        
        return quote
    
    def _fetch_quote_tencent(self, stock_code: str) -> Optional[Dict]:
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
            
            return {
                "stock_code": stock_code,
                "name": parts[1] if len(parts) > 1 else stock_code,
                "price": float(parts[3]) if len(parts) > 3 else 0,
                "open": float(parts[5]) if len(parts) > 5 else 0,
                "high": float(parts[33]) if len(parts) > 33 else 0,
                "low": float(parts[34]) if len(parts) > 34 else 0,
                "pre_close": float(parts[4]) if len(parts) > 4 else 0,
                "volume": int(float(parts[6])) if len(parts) > 6 else 0,
                "amount": float(parts[37]) if len(parts) > 37 else 0,
                "bid_price": float(parts[9]) if len(parts) > 9 else 0,
                "ask_price": float(parts[18]) if len(parts) > 18 else 0,
                "change": float(parts[31]) if len(parts) > 31 else 0,
                "change_percent": float(parts[32]) if len(parts) > 32 else 0
            }
        except Exception as e:
            # 返回模拟数据
            return {
                "stock_code": stock_code,
                "name": stock_code,
                "price": 10.0 + random.uniform(-1, 1),
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "pre_close": 10.0,
                "volume": random.randint(100000, 1000000),
                "amount": random.uniform(1000000, 10000000),
                "bid_price": 10.0,
                "ask_price": 10.01,
                "change": random.uniform(-0.5, 0.5),
                "change_percent": random.uniform(-5, 5)
            }
    
    def calculate_commission(self, amount: float, is_sell: bool = False) -> float:
        """计算手续费"""
        # 佣金 万分之2.5，最低5元
        commission = amount * self._commission_rate
        if commission < 5:
            commission = 5
        
        # 印花税 千分之一（仅卖出）
        if is_sell:
            commission += amount * 0.001
        
        # 过户费 万分之一
        commission += amount * 0.00001
        
        return round(commission, 2)
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态"""
        return {
            "balance": self._balance,
            "frozen": self._frozen,
            "positions": self._positions,
            "orders": self._orders,
            "saved_at": datetime.now().isoformat()
        }
    
    def load_state(self, state: Dict[str, Any]):
        """加载状态"""
        self._balance = state.get("balance", self.DEFAULT_BALANCE)
        self._frozen = state.get("frozen", 0)
        self._positions = state.get("positions", {})
        self._orders = state.get("orders", {})


# 全局实例
broker = SyncBrokerWrapper.get_instance()