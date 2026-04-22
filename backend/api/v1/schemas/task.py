"""
Task API Schemas (Pydantic models)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskCreate(BaseModel):
    """Schema for creating a task"""
    framework: str = Field(..., description="Framework (pytorch/tensorflow/jax)")
    gpu_required: int = Field(default=1, ge=1, description="Number of GPUs required")
    duration_hours: int = Field(default=1, ge=1, le=720, description="Duration in hours")
    memory_required_gb: int = Field(default=8, ge=1, description="Required memory in GB")
    code_url: Optional[str] = Field(None, description="URL to code repository")
    data_url: Optional[str] = Field(None, description="URL to input data")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Task parameters")


class TaskResponse(BaseModel):
    """Schema for task API response"""
    id: str
    user_id: str
    status: str
    node_id: Optional[str]
    framework: str
    gpu_required: int
    duration_hours: int
    result_path: Optional[str]
    error_message: Optional[str]
    gpu_hours_consumed: float
    cost_usd: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for task list response"""
    tasks: list[TaskResponse]
    total: int
