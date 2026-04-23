# ComputeHub API v1 - Node Schemas
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NodeBase(BaseModel):
    name: str
    gpu_model: Optional[str] = None
    gpu_count: int = 0
    cpu_cores: int = 0
    memory_gb: int = 0
    country: Optional[str] = None
    city: Optional[str] = None


class NodeCreate(NodeBase):
    pass


class NodeUpdate(BaseModel):
    status: Optional[str] = None
    gpu_model: Optional[str] = None
    gpu_count: Optional[int] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    gpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    network_latency_ms: Optional[float] = None


class NodeResponse(NodeBase):
    id: str
    status: str
    gpu_utilization: float
    memory_utilization: float
    network_latency_ms: float
    is_active: bool
    last_heartbeat: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
