# ComputeHub Models - Compute Node
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from src.core.database import Base
from src.models.base import TimestampMixin


class Node(TimestampMixin, Base):
    """ComputeNode model - represents a GPU/CPU compute node."""
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)  # UUID as string
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="offline")  # online, offline, busy, maintenance
    gpu_model = Column(String(255))
    gpu_count = Column(Integer, default=0)
    cpu_cores = Column(Integer, default=0)
    memory_gb = Column(Integer, default=0)
    country = Column(String(100))
    city = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    last_heartbeat = Column(DateTime)
    gpu_utilization = Column(Float, default=0.0)
    memory_utilization = Column(Float, default=0.0)
    network_latency_ms = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    # Relationships
    tasks = relationship("Task", back_populates="node")
