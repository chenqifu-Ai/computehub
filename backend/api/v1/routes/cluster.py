"""
集群管理 API - 查看集群状态和统计信息
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import async_session_maker
from backend.services.scheduler import SmartScheduler
import structlog

logger = structlog.get_logger()

router = APIRouter()


async def get_db():
    """Database dependency"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@router.get("/stats", response_model=dict)
async def get_cluster_stats(db=Depends(get_db)):
    """获取集群统计信息"""
    stats = await SmartScheduler.get_cluster_stats(db)
    
    return {
        "success": True,
        "data": stats
    }


@router.get("/status", response_model=dict)
async def get_cluster_status(db=Depends(get_db)):
    """获取集群详细状态"""
    stats = await SmartScheduler.get_cluster_stats(db)
    
    # 计算健康度
    if stats["total_nodes"] == 0:
        health = "unknown"
        health_score = 0
    else:
        online_ratio = stats["online_nodes"] / stats["total_nodes"]
        if online_ratio >= 0.9:
            health = "excellent"
            health_score = 100
        elif online_ratio >= 0.7:
            health = "good"
            health_score = 80
        elif online_ratio >= 0.5:
            health = "fair"
            health_score = 60
        else:
            health = "poor"
            health_score = 40
    
    return {
        "success": True,
        "data": {
            **stats,
            "cluster_health": health,
            "health_score": health_score,
        }
    }
