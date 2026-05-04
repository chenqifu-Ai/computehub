"""
交易路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import db
from ..services import market_service
from ..core.dependencies import get_current_user

router = APIRouter()


class OrderCreate(BaseModel):
    stock_code: str
    order_type: str  # buy, sell
    price: Optional[float] = None
    volume: int


@router.post("/buy")
async def buy_stock(
    stock_code: str,
    volume: int,
    price: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """买入股票"""
    user_id = current_user["id"]
    
    # 获取账户
    account = db.get_account(user_id)
    if not account:
        account = {"balance": 1000000.0}
    
    # 获取股票信息
    stock = db.get_stock(stock_code)
    if not stock:
        # 尝试从市场服务获取
        stocks = market_service.search_stocks(stock_code)
        if stocks:
            stock = stocks[0]
        else:
            stock = {"code": stock_code, "name": stock_code}
    
    # 获取当前价格
    if price is None:
        quote = market_service.get_quote(stock_code)
        price = quote.get("price", 10.0) if quote else 10.0
    
    # 检查余额
    amount = price * volume
    if amount > account.get("balance", 0):
        return {"code": 400, "message": "余额不足"}
    
    # 更新余额
    new_balance = account.get("balance", 0) - amount
    db.update_balance(user_id, new_balance)
    
    # 更新持仓
    positions = db.get_positions(user_id)
    existing_pos = None
    for pos in positions:
        if pos["stock_code"] == stock_code:
            existing_pos = pos
            break
    
    if existing_pos:
        # 计算新成本价
        total_cost = existing_pos["cost_price"] * existing_pos["volume"] + amount
        total_volume = existing_pos["volume"] + volume
        new_cost_price = total_cost / total_volume
        db.update_position(user_id, stock_code, total_volume, new_cost_price)
    else:
        db.update_position(user_id, stock_code, volume, price)
    
    # 创建订单
    db.create_order(user_id, stock_code, "buy", price, volume)
    
    return {
        "code": 200,
        "message": "买入成功",
        "data": {
            "stock_code": stock_code,
            "stock_name": stock.get("name", stock_code),
            "volume": volume,
            "price": price,
            "amount": round(amount, 2)
        }
    }


@router.post("/sell")
async def sell_stock(
    stock_code: str,
    volume: int,
    price: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """卖出股票"""
    user_id = current_user["id"]
    
    # 获取持仓
    positions = db.get_positions(user_id)
    existing_pos = None
    for pos in positions:
        if pos["stock_code"] == stock_code:
            existing_pos = pos
            break
    
    if not existing_pos:
        return {"code": 400, "message": "没有该股票持仓"}
    
    if volume > existing_pos["volume"]:
        return {"code": 400, "message": "卖出数量超过持仓数量"}
    
    # 获取股票信息
    stock = db.get_stock(stock_code)
    if not stock:
        stock = {"code": stock_code, "name": stock_code}
    
    # 获取当前价格
    if price is None:
        quote = market_service.get_quote(stock_code)
        price = quote.get("price", 10.0) if quote else 10.0
    
    # 计算金额
    amount = price * volume
    
    # 更新余额
    account = db.get_account(user_id)
    new_balance = account.get("balance", 0) + amount
    db.update_balance(user_id, new_balance)
    
    # 更新持仓
    new_volume = existing_pos["volume"] - volume
    if new_volume > 0:
        db.update_position(user_id, stock_code, new_volume, existing_pos["cost_price"])
    else:
        db.execute("DELETE FROM positions WHERE user_id = ? AND stock_code = ?", (user_id, stock_code))
    
    # 创建订单
    db.create_order(user_id, stock_code, "sell", price, volume)
    
    return {
        "code": 200,
        "message": "卖出成功",
        "data": {
            "stock_code": stock_code,
            "stock_name": stock.get("name", stock_code),
            "volume": volume,
            "price": price,
            "amount": round(amount, 2)
        }
    }


@router.get("/orders")
async def get_orders(current_user: dict = Depends(get_current_user)):
    """获取订单列表"""
    user_id = current_user["id"]
    orders = db.get_orders(user_id)
    
    order_list = []
    for order in orders:
        stock = db.get_stock(order["stock_code"]) or {"name": order["stock_code"]}
        order_list.append({
            "id": order["id"],
            "stock_code": order["stock_code"],
            "stock_name": stock.get("name", order["stock_code"]),
            "order_type": order["order_type"],
            "order_price": round(order["order_price"], 2),
            "order_volume": order["order_volume"],
            "status": order["status"],
            "created_at": order["created_at"]
        })
    
    return {"code": 200, "data": {"list": order_list}}


@router.get("/positions")
async def get_positions(current_user: dict = Depends(get_current_user)):
    """获取持仓"""
    user_id = current_user["id"]
    positions = db.get_positions(user_id)
    
    position_list = []
    for pos in positions:
        stock = db.get_stock(pos["stock_code"]) or {"name": pos["stock_code"]}
        quote = market_service.get_quote(pos["stock_code"])
        current_price = quote.get("price", pos["cost_price"]) if quote else pos["cost_price"]
        
        position_list.append({
            "stock_code": pos["stock_code"],
            "stock_name": stock.get("name", pos["stock_code"]),
            "volume": pos["volume"],
            "cost_price": round(pos["cost_price"], 2),
            "current_price": round(current_price, 2),
            "market_value": round(current_price * pos["volume"], 2),
            "profit": round((current_price - pos["cost_price"]) * pos["volume"], 2)
        })
    
    return {"code": 200, "data": {"list": position_list}}