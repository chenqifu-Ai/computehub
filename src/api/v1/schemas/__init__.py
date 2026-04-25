"""Pydantic Schemas"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# === User ===
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# === Node ===
class NodeRegister(BaseModel):
    node_id: str = Field(..., min_length=1, max_length=64)
    name: str
    gpu_count: int = 0
    memory_gb: int = 0
    cpu_cores: int = 0


class NodeStatusUpdate(BaseModel):
    node_id: str
    gpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    cpu_utilization: Optional[float] = None
    queue_depth: Optional[int] = None


class NodeResponse(BaseModel):
    id: str
    name: str
    status: str
    gpu_count: int
    gpu_utilization: float
    memory_gb: int
    memory_utilization: float
    cpu_cores: int
    cpu_utilization: float
    queue_depth: int
    last_heartbeat: Optional[datetime] = None

    model_config = {"from_attributes": True}


# === Task ===
class TaskCreate(BaseModel):
    action: str = Field(..., min_length=1, max_length=50)
    payload: dict = Field(default_factory=dict)
    priority: str = "MEDIUM"


class TaskResponse(BaseModel):
    id: str
    user_id: int
    action: str
    status: str
    priority: str
    assigned_node: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
