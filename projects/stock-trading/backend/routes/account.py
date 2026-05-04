"""
账户路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import db
from ..core.dependencies import get_current_user

router = APIRouter()


class AccountInfo(BaseModel):
    balance: float
    frozen: float
    market_value: float
    total_asset: float
    total_profit: float
    total_profit_percent: float


class PositionInfo(BaseModel):
    stock_code: str
    stock_name: str
    volume: int
    available_volume: int
    cost_price: float
    current_price: float
    market_value: float
    profit: float
    profit_percent: float


class OrderInfo(BaseModel):
    id: int
    stock_code: str
    stock_name: str
    order_type: str
    order_price: float
    order_volume: int
    filled_volume: int
    status: str
    created_at: str


@router.get("/info")
async def get_account_info(current_user: dict = Depends(get_current_user)):
    """获取账户信息"""
    user_id = current_user["id"]
    
    # 获取账户
    account = db.get_account(user_id)
    if not account:
        # 创建默认账户
        db.execute(
            "INSERT INTO accounts (user_id, balance) VALUES (?, ?)",
            (user_id, 1000000.0)
        )
        account = {"balance": 1000000.0, "frozen": 0.0}
    
    # 获取持仓
    positions = db.get_positions(user_id)
    
    # 计算市值和盈亏
    market_value = 0.0
    total_profit = 0.0
    
    position_list = []
    for pos in positions:
        # 获取当前价格（模拟）
        current_price = pos.get("cost_price", 0) * (1 + (datetime.now().second % 10 - 5) / 100)
        
        pos_market_value = current_price * pos["volume"]
        pos_profit = (current_price - pos["cost_price"]) * pos["volume"]
        
        market_value += pos_market_value
        total_profit += pos_profit
        
        position_list.append({
            "stock_code": pos["stock_code"],
            "stock_name": pos.get("stock_name", pos["stock_code"]),
            "volume": pos["volume"],
            "available_volume": pos.get("available_volume", pos["volume"]),
            "cost_price": round(pos["cost_price"], 2),
            "current_price": round(current_price, 2),
            "market_value": round(pos_market_value, 2),
            "profit": round(pos_profit, 2),
            "profit_percent": round((current_price / pos["cost_price"] - 1) * 100, 2) if pos["cost_price"] > 0 else 0
        })
    
    total_asset = account.get("balance", 0) + market_value
    initial_capital = 1000000.0
    total_profit_percent = round((total_asset / initial_capital - 1) * 100, 2) if initial_capital > 0 else 0
    
    return {
        "code": 200,
        "data": {
            "account": {
                "balance": round(account.get("balance", 0), 2),
                "frozen": round(account.get("frozen", 0), 2),
                "market_value": round(market_value, 2),
                "total_asset": round(total_asset, 2),
                "total_profit": round(total_profit, 2),
                "total_profit_percent": total_profit_percent
            },
            "positions": position_list
        }
    }


@router.get("/positions")
async def get_positions(current_user: dict = Depends(get_current_user)):
    """获取持仓列表"""
    user_id = current_user["id"]
    positions = db.get_positions(user_id)
    
    position_list = []
    for pos in positions:
        current_price = pos.get("cost_price", 0) * (1 + (datetime.now().second % 10 - 5) / 100)
        pos_market_value = current_price * pos["volume"]
        pos_profit = (current_price - pos["cost_price"]) * pos["volume"]
        
        position_list.append({
            "stock_code": pos["stock_code"],
            "stock_name": pos.get("stock_name", pos["stock_code"]),
            "volume": pos["volume"],
            "cost_price": round(pos["cost_price"], 2),
            "current_price": round(current_price, 2),
            "market_value": round(pos_market_value, 2),
            "profit": round(pos_profit, 2),
            "profit_percent": round((current_price / pos["cost_price"] - 1) * 100, 2) if pos["cost_price"] > 0 else 0
        })
    
    return {"code": 200, "data": {"list": position_list}}


@router.get("/orders")
async def get_orders(current_user: dict = Depends(get_current_user), limit: int = 50):
    """获取订单列表"""
    user_id = current_user["id"]
    orders = db.get_orders(user_id, limit=limit)
    
    order_list = []
    for order in orders:
        order_list.append({
            "id": order["id"],
            "stock_code": order["stock_code"],
            "stock_name": order.get("stock_name", order["stock_code"]),
            "order_type": order["order_type"],
            "order_price": round(order["order_price"], 2),
            "order_volume": order["order_volume"],
            "filled_volume": order.get("filled_volume", 0),
            "status": order["status"],
            "created_at": order["created_at"]
        })
    
    return {"code": 200, "data": {"list": order_list}}


@router.post("/deposit")
async def deposit(amount: float, current_user: dict = Depends(get_current_user)):
    """充值"""
    user_id = current_user["id"]
    account = db.get_account(user_id)
    
    if not account:
        db.execute(
            "INSERT INTO accounts (user_id, balance) VALUES (?, ?)",
            (user_id, amount)
        )
    else:
        new_balance = account["balance"] + amount
        db.update_balance(user_id, new_balance)
    
    return {"code": 200, "message": "充值成功", "data": {"amount": amount}}