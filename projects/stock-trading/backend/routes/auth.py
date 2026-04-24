"""
认证路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import jwt
from datetime import datetime, timedelta

from ..database import db
from ..config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS

router = APIRouter()


class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    """简单密码哈希"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(user_id: int, username: str) -> str:
    """创建JWT令牌"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register")
async def register(user: UserRegister):
    """用户注册"""
    # 检查用户名是否存在
    existing = db.get_user(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user_id = db.create_user(
        username=user.username,
        password=hash_password(user.password),
        email=user.email
    )
    
    # 创建账户
    db.execute(
        "INSERT INTO accounts (user_id, balance) VALUES (?, 1000000.00)",
        (user_id,)
    )
    
    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            "user_id": user_id,
            "username": user.username
        }
    }


@router.post("/login")
async def login(user: UserLogin):
    """用户登录"""
    # 查询用户
    db_user = db.get_user(user.username)
    if not db_user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 验证密码
    if db_user["password"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 创建令牌
    token = create_token(db_user["id"], db_user["username"])
    
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "token": token,
            "user": {
                "id": db_user["id"],
                "username": db_user["username"],
                "email": db_user["email"]
            }
        }
    }


@router.get("/info")
async def get_user_info(current_user: dict = Depends(lambda: None)):
    """获取用户信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未认证")
    
    return {
        "code": 200,
        "data": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user.get("email")
        }
    }