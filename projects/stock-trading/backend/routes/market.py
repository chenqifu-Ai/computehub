"""
市场数据路由
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from ..services import market_service
from ..core.dependencies import get_current_user_optional

router = APIRouter()


@router.get("/stocks")
async def get_stocks(
    keyword: Optional[str] = None,
    market: Optional[str] = None
):
    """获取股票列表"""
    stocks = market_service.get_stock_list(keyword=keyword, market=market)
    
    return {
        "code": 200,
        "data": {
            "list": stocks,
            "total": len(stocks)
        }
    }


@router.get("/quote/{code}")
async def get_quote(code: str):
    """获取实时行情"""
    quote = market_service.get_quote(code)
    
    return {
        "code": 200,
        "data": quote
    }


@router.get("/quotes")
async def get_quotes(codes: str = Query(..., description="股票代码，逗号分隔")):
    """批量获取行情"""
    code_list = [c.strip() for c in codes.split(",")]
    quotes = market_service.get_quotes(code_list)
    
    return {
        "code": 200,
        "data": {
            "list": quotes,
            "total": len(quotes)
        }
    }


@router.get("/kline/{code}")
async def get_kline(
    code: str,
    period: str = Query("daily", description="周期: daily/weekly/monthly"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    count: int = Query(100, description="数据条数")
):
    """获取K线数据"""
    kline = market_service.get_kline(
        code=code,
        period=period,
        start_date=start_date,
        end_date=end_date,
        count=count
    )
    
    return {
        "code": 200,
        "data": kline
    }


@router.get("/search")
async def search_stocks(keyword: str = Query(..., description="搜索关键词")):
    """搜索股票"""
    results = market_service.search_stocks(keyword)
    
    return {
        "code": 200,
        "data": {
            "list": results,
            "total": len(results)
        }
    }


@router.get("/hot")
async def get_hot_stocks(limit: int = Query(10, description="返回条数")):
    """获取热门股票"""
    stocks = market_service.get_hot_stocks(limit=limit)
    
    return {
        "code": 200,
        "data": {
            "list": stocks,
            "total": len(stocks)
        }
    }


@router.get("/industry/{industry}")
async def get_industry_stocks(industry: str):
    """获取行业股票"""
    stocks = market_service.get_industry_stocks(industry)
    
    return {
        "code": 200,
        "data": {
            "industry": industry,
            "list": stocks,
            "total": len(stocks)
        }
    }


@router.get("/summary")
async def get_market_summary():
    """获取市场概况"""
    summary = market_service.get_market_summary()
    
    return {
        "code": 200,
        "data": summary
    }


@router.get("/stock/{code}")
async def get_stock_info(code: str):
    """获取股票信息"""
    stock = market_service.get_stock_info(code)
    
    if not stock:
        return {
            "code": 404,
            "message": "股票不存在"
        }
    
    # 同时获取行情
    quote = market_service.get_quote(code)
    stock["quote"] = quote
    
    return {
        "code": 200,
        "data": stock
    }