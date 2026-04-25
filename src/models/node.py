"""Node 模型"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, func, Enum as SAEnum
import enum

from src.core.database import Base


class NodeStatus(str, enum.Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class Node(Base):
    __tablename__ = "nodes"

    id = Column(String(64), primary_key=True)  # node_id
    name = Column(String(100), nullable=False)
    status = Column(SAEnum(NodeStatus), default=NodeStatus.OFFLINE, nullable=False)
    gpu_count = Column(Integer, default=0)
    gpu_utilization = Column(Float, default=0.0)
    memory_gb = Column(Integer, default=0)
    memory_utilization = Column(Float, default=0.0)
    cpu_cores = Column(Integer, default=0)
    cpu_utilization = Column(Float, default=0.0)
    queue_depth = Column(Integer, default=0)
    last_heartbeat = Column(DateTime, nullable=True)
    owner_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
