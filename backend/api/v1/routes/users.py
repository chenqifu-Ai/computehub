"""
User API Routes
"""

from fastapi import APIRouter

from backend.models.base import async_session_maker
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


@router.get("/me")
async def get_current_user_info():
    """Get current user information (placeholder)"""
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "email": "demo@computehub.io",
        "username": "demo_user",
        "balance_usd": 100.0,
    }
