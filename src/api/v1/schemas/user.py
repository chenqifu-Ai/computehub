# ComputeHub API v1 - User Schemas
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: str
    username: str
    full_name: Optional[str] = None
    company: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    company: Optional[str] = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    balance_usd: float
    total_spent_usd: float
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}
