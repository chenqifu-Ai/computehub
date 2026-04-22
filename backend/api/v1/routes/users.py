"""
User API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User
from backend.models.base import get_db
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/me")
async def get_current_user_info(db: AsyncSession = get_db):
    """
    Get current user information
    
    TODO: Implement proper authentication
    Currently returns a placeholder user
    """
    # Temporary placeholder - will be replaced with auth
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "email": "demo@computehub.io",
        "username": "demo_user",
        "balance_usd": 100.0,
    }
