# ComputeHub API v1 - Task Schemas
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskBase(BaseModel):
    framework: str = "pytorch"
    gpu_required: int = 1
    duration_hours: int = 1
    memory_required_gb: int = 8
    code_url: Optional[str] = None
    data_url: Optional[str] = None
    parameters: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    parameters: Optional[str] = None


class TaskResponse(TaskBase):
    id: str
    user_id: str
    status: str
    node_id: Optional[str] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    gpu_hours_consumed: float
    cost_usd: float

    model_config = {"from_attributes": True}
