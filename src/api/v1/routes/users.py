"""用户路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.user import User
from src.api.auth import get_current_user
from src.api.v1.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """用户列表（需认证）"""
    return [UserResponse.model_validate(u) for u in db.query(User).all()]
