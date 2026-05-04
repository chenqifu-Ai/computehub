"""
策略管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from ..database import db
from ..core.dependencies import get_current_user
from ..services.backtest_engine import BacktestEngine

router = APIRouter()


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    code: str
    params: Optional[dict] = None


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    params: Optional[dict] = None
    status: Optional[str] = None


class BacktestRequest(BaseModel):
    stock_code: str
    start_date: str
    end_date: str
    initial_capital: float = 1000000.0


@router.get("/list")
async def list_strategies(current_user: dict = Depends(get_current_user)):
    """获取策略列表"""
    strategies = db.get_strategies(current_user["id"])
    
    # 补充回测统计
    for strategy in strategies:
        backtests = db.get_backtests(strategy["id"], limit=10)
        strategy["backtest_count"] = len(backtests)
        if backtests:
            strategy["last_return"] = backtests[0].get("total_return", 0)
        else:
            strategy["last_return"] = None
    
    return {
        "code": 200,
        "data": {
            "list": strategies,
            "total": len(strategies)
        }
    }


@router.post("/create")
async def create_strategy(
    strategy: StrategyCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建策略"""
    # 验证策略代码安全性
    if not validate_strategy_code(strategy.code):
        return {"code": 400, "message": "策略代码包含不安全操作"}
    
    strategy_id = db.create_strategy(
        user_id=current_user["id"],
        name=strategy.name,
        code=strategy.code,
        description=strategy.description
    )
    
    return {
        "code": 200,
        "message": "策略创建成功",
        "data": {
            "strategy_id": strategy_id
        }
    }


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取策略详情"""
    strategy = db.get_strategy(strategy_id)
    
    if not strategy:
        return {"code": 404, "message": "策略不存在"}
    
    if strategy["user_id"] != current_user["id"]:
        return {"code": 403, "message": "无权访问此策略"}
    
    # 获取回测历史
    backtests = db.get_backtests(strategy_id, limit=10)
    strategy["backtests"] = backtests
    
    return {
        "code": 200,
        "data": strategy
    }


@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    strategy_update: StrategyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新策略"""
    strategy = db.get_strategy(strategy_id)
    
    if not strategy:
        return {"code": 404, "message": "策略不存在"}
    
    if strategy["user_id"] != current_user["id"]:
        return {"code": 403, "message": "无权修改此策略"}
    
    # 构建更新字段
    update_fields = {}
    if strategy_update.name:
        update_fields["name"] = strategy_update.name
    if strategy_update.description is not None:
        update_fields["description"] = strategy_update.description
    if strategy_update.code:
        if not validate_strategy_code(strategy_update.code):
            return {"code": 400, "message": "策略代码包含不安全操作"}
        update_fields["code"] = strategy_update.code
    if strategy_update.status:
        if strategy_update.status not in ["draft", "active", "stopped"]:
            return {"code": 400, "message": "无效的状态"}
        update_fields["status"] = strategy_update.status
    
    if update_fields:
        db.update_strategy(strategy_id, **update_fields)
    
    return {
        "code": 200,
        "message": "策略更新成功"
    }


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除策略"""
    strategy = db.get_strategy(strategy_id)
    
    if not strategy:
        return {"code": 404, "message": "策略不存在"}
    
    if strategy["user_id"] != current_user["id"]:
        return {"code": 403, "message": "无权删除此策略"}
    
    db.delete_strategy(strategy_id)
    
    return {
        "code": 200,
        "message": "策略删除成功"
    }


@router.post("/{strategy_id}/backtest")
async def run_backtest(
    strategy_id: int,
    backtest_req: BacktestRequest,
    current_user: dict = Depends(get_current_user)
):
    """运行回测"""
    strategy = db.get_strategy(strategy_id)
    
    if not strategy:
        return {"code": 404, "message": "策略不存在"}
    
    if strategy["user_id"] != current_user["id"]:
        return {"code": 403, "message": "无权使用此策略"}
    
    # 运行回测
    engine = BacktestEngine()
    result = engine.run_backtest(
        strategy_code=strategy["code"],
        stock_code=backtest_req.stock_code,
        start_date=backtest_req.start_date,
        end_date=backtest_req.end_date,
        initial_capital=backtest_req.initial_capital
    )
    
    if not result.get("success"):
        return {
            "code": 400,
            "message": result.get("error", "回测运行失败")
        }
    
    # 保存回测结果
    db.save_backtest(
        strategy_id=strategy_id,
        stock_code=backtest_req.stock_code,
        start_date=backtest_req.start_date,
        end_date=backtest_req.end_date,
        initial_capital=backtest_req.initial_capital,
        final_capital=result["final_capital"],
        total_return=result["total_return"],
        max_drawdown=result["max_drawdown"],
        sharpe_ratio=result["sharpe_ratio"],
        win_rate=result["win_rate"],
        total_trades=result["total_trades"]
    )
    
    return {
        "code": 200,
        "message": "回测完成",
        "data": result
    }


@router.get("/{strategy_id}/backtests")
async def get_backtests(
    strategy_id: int,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """获取策略的回测历史"""
    strategy = db.get_strategy(strategy_id)
    
    if not strategy:
        return {"code": 404, "message": "策略不存在"}
    
    if strategy["user_id"] != current_user["id"]:
        return {"code": 403, "message": "无权访问此策略"}
    
    backtests = db.get_backtests(strategy_id, limit=limit)
    
    return {
        "code": 200,
        "data": {
            "list": backtests,
            "total": len(backtests)
        }
    }


@router.post("/{strategy_id}/start")
async def start_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_user)
):
    """启动策略"""
    strategy = db.get_strategy(strategy_id)
    
    if not strategy:
        return {"code": 404, "message": "策略不存在"}
    
    if strategy["user_id"] != current_user["id"]:
        return {"code": 403, "message": "无权操作此策略"}
    
    # 更新状态为运行中
    db.update_strategy(strategy_id, status="running")
    
    return {
        "code": 200,
        "message": "策略已启动"
    }


@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_user)
):
    """停止策略"""
    strategy = db.get_strategy(strategy_id)
    
    if not strategy:
        return {"code": 404, "message": "策略不存在"}
    
    if strategy["user_id"] != current_user["id"]:
        return {"code": 403, "message": "无权操作此策略"}
    
    # 更新状态为已停止
    db.update_strategy(strategy_id, status="stopped")
    
    return {
        "code": 200,
        "message": "策略已停止"
    }


def validate_strategy_code(code: str) -> bool:
    """验证策略代码安全性"""
    # 禁止的危险操作
    forbidden = [
        "import os",
        "import sys",
        "import subprocess",
        "import shutil",
        "import glob",
        "exec(",
        "eval(",
        "compile(",
        "open(",
        "__import__",
        "globals()",
        "locals()",
        "getattr(",
        "setattr(",
        "delattr(",
        "del ",
        "class ",
        "def ",
        "lambda ",
        "yield ",
        "raise ",
        "assert ",
    ]
    
    code_lower = code.lower()
    for f in forbidden:
        if f.lower() in code_lower:
            return False
    
    return True