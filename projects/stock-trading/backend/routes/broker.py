"""
券商交易接口路由
支持模拟/实盘切换
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..brokers import BrokerRegistry, AVAILABLE_BROKERS
from ..brokers.base import TradeDirection, OrderType, OrderStatus

router = APIRouter()


# ============ 请求模型 ============

class BrokerConfig(BaseModel):
    broker_id: str
    config: dict = {}


class OrderRequest(BaseModel):
    stock_code: str
    direction: str  # buy, sell
    volume: int
    price: Optional[float] = None
    order_type: str = "limit"  # limit, market


# ============ 券商管理 ============

@router.get("/list")
async def list_brokers():
    """列出所有可用券商"""
    brokers = BrokerRegistry.list_brokers()
    
    result = []
    for broker_id, broker_name in brokers.items():
        broker_class = AVAILABLE_BROKERS.get(broker_id)
        result.append({
            "id": broker_id,
            "name": broker_name,
            "supports_margin": getattr(broker_class, 'SUPPORTS_MARGIN', False) if broker_class else False,
            "supports_short": getattr(broker_class, 'SUPPORTS_SHORT', False) if broker_class else False
        })
    
    return {"code": 200, "data": {"brokers": result}}


@router.get("/current")
async def get_current_broker():
    """获取当前券商"""
    current = BrokerRegistry.get_default()
    brokers = BrokerRegistry.list_brokers()
    
    return {
        "code": 200,
        "data": {
            "current_broker": current,
            "current_name": brokers.get(current, current)
        }
    }


@router.post("/switch")
async def switch_broker(broker_id: str):
    """切换券商"""
    if broker_id not in AVAILABLE_BROKERS:
        return {"code": 400, "message": f"不支持的券商: {broker_id}"}
    
    BrokerRegistry.set_default(broker_id)
    
    return {
        "code": 200,
        "message": f"已切换到 {BrokerRegistry.list_brokers().get(broker_id, broker_id)}"
    }


# ============ 账户接口 ============

@router.get("/account")
async def get_broker_account():
    """获取券商账户信息"""
    try:
        broker = await BrokerRegistry.get_instance()
        account = await broker.get_account_info()
        
        return {
            "code": 200,
            "data": account.to_dict()
        }
    except Exception as e:
        return {"code": 500, "message": f"获取账户失败: {str(e)}"}


@router.get("/positions")
async def get_broker_positions():
    """获取券商持仓"""
    try:
        broker = await BrokerRegistry.get_instance()
        positions = await broker.get_positions()
        
        return {
            "code": 200,
            "data": {
                "list": [pos.to_dict() for pos in positions]
            }
        }
    except Exception as e:
        return {"code": 500, "message": f"获取持仓失败: {str(e)}"}


# ============ 交易接口 ============

@router.post("/order")
async def place_order(req: OrderRequest):
    """下单"""
    try:
        broker = await BrokerRegistry.get_instance()
        
        # 验证方向
        direction = TradeDirection.BUY if req.direction.lower() == "buy" else TradeDirection.SELL
        
        # 验证订单类型
        order_type = OrderType.MARKET if req.order_type.lower() == "market" else OrderType.LIMIT
        
        # 下单
        result = await broker.place_order(
            stock_code=req.stock_code,
            direction=direction,
            volume=req.volume,
            price=req.price,
            order_type=order_type
        )
        
        return {
            "code": 200 if result.success else 400,
            "message": result.message,
            "data": result.to_dict() if result.success else None
        }
    except Exception as e:
        return {"code": 500, "message": f"下单失败: {str(e)}"}


@router.post("/order/{order_id}/cancel")
async def cancel_order(order_id: str):
    """撤单"""
    try:
        broker = await BrokerRegistry.get_instance()
        success = await broker.cancel_order(order_id)
        
        return {
            "code": 200 if success else 400,
            "message": "撤单成功" if success else "撤单失败"
        }
    except Exception as e:
        return {"code": 500, "message": f"撤单失败: {str(e)}"}


@router.get("/orders")
async def get_orders(status: str = None, limit: int = 50):
    """获取订单列表"""
    try:
        broker = await BrokerRegistry.get_instance()
        
        # 转换状态
        order_status = None
        if status:
            status_map = {
                "pending": OrderStatus.PENDING,
                "submitted": OrderStatus.SUBMITTED,
                "partial": OrderStatus.PARTIAL,
                "filled": OrderStatus.FILLED,
                "cancelled": OrderStatus.CANCELLED,
                "rejected": OrderStatus.REJECTED,
            }
            order_status = status_map.get(status.lower())
        
        orders = await broker.get_orders(status=order_status, limit=limit)
        
        return {
            "code": 200,
            "data": {
                "list": [order.to_dict() for order in orders]
            }
        }
    except Exception as e:
        return {"code": 500, "message": f"获取订单失败: {str(e)}"}


# ============ 行情接口 ============

@router.get("/quote/{stock_code}")
async def get_broker_quote(stock_code: str):
    """获取实时行情"""
    try:
        broker = await BrokerRegistry.get_instance()
        quote = await broker.get_quote(stock_code)
        
        if quote is None:
            return {"code": 404, "message": f"无法获取股票行情: {stock_code}"}
        
        return {
            "code": 200,
            "data": quote.to_dict()
        }
    except Exception as e:
        return {"code": 500, "message": f"获取行情失败: {str(e)}"}


@router.post("/quotes")
async def get_broker_quotes(stock_codes: List[str]):
    """批量获取行情"""
    try:
        broker = await BrokerRegistry.get_instance()
        quotes = await broker.get_quotes(stock_codes)
        
        return {
            "code": 200,
            "data": {
                "list": [quote.to_dict() for quote in quotes]
            }
        }
    except Exception as e:
        return {"code": 500, "message": f"获取行情失败: {str(e)}"}


# ============ 状态持久化 ============

@router.post("/state/save")
async def save_state():
    """保存模拟账户状态"""
    try:
        state = BrokerRegistry.save_state(BrokerRegistry.get_default())
        
        # 保存到文件
        import json
        import os
        
        state_file = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'data', 
            'broker_state.json'
        )
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        return {"code": 200, "message": "状态保存成功"}
    except Exception as e:
        return {"code": 500, "message": f"保存失败: {str(e)}"}


@router.post("/state/load")
async def load_state():
    """加载模拟账户状态"""
    try:
        import json
        import os
        
        state_file = os.path.join(
            os.path.dirname(__file__),
            '..',
            'data',
            'broker_state.json'
        )
        
        if not os.path.exists(state_file):
            return {"code": 404, "message": "状态文件不存在"}
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        BrokerRegistry.load_state(BrokerRegistry.get_default(), state)
        
        return {"code": 200, "message": "状态加载成功"}
    except Exception as e:
        return {"code": 500, "message": f"加载失败: {str(e)}"}