"""
Node API Schemas (Pydantic models)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class NodeStatusEnum(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class NodeRegister(BaseModel):
    """Schema for node registration"""
    name: str = Field(..., min_length=1, max_length=255, description="Node name")
    gpu_model: Optional[str] = Field(None, description="GPU model (e.g., RTX 4090)")
    gpu_count: int = Field(default=1, ge=1, description="Number of GPUs")
    cpu_cores: int = Field(default=4, ge=1, description="Number of CPU cores")
    memory_gb: int = Field(default=16, ge=1, description="Memory in GB")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class NodeHeartbeat(BaseModel):
    """Schema for node heartbeat report"""
    gpu_utilization: float = Field(ge=0, le=100, description="GPU utilization percentage")
    memory_utilization: float = Field(ge=0, le=100, description="Memory utilization percentage")
    network_latency_ms: float = Field(ge=0, description="Network latency to gateway in ms")
    gpu_temperature: Optional[float] = Field(None, ge=0, description="GPU temperature in Celsius")
    available_memory_gb: Optional[float] = Field(None, ge=0, description="Available memory in GB")


class NodeResponse(BaseModel):
    """Schema for node API response"""
    id: str
    name: str
    status: str
    gpu_model: str | None
    gpu_count: int
    cpu_cores: int
    memory_gb: int
    location: dict | None = None
    metrics: dict | None = None
    last_heartbeat: datetime | None = None
    created_at: datetime | None = None
    
    class Config:
        from_attributes = True


class NodeListResponse(BaseModel):
    """Schema for node list response"""
    nodes: list[NodeResponse]
    total: int
