"""
Node Model - Represents compute nodes in the network
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.models.base import Base
import uuid
import datetime


class Node(Base):
    """Compute node model"""
    
    __tablename__ = "nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    
    # Status
    status = Column(String(50), default="offline", index=True)  # online/offline/maintenance
    
    # Hardware specs
    gpu_model = Column(String(255))
    gpu_count = Column(Integer, default=0)
    cpu_cores = Column(Integer, default=0)
    memory_gb = Column(Integer, default=0)
    
    # Location (for geo-based scheduling)
    country = Column(String(100))
    city = Column(String(100))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Heartbeat tracking
    last_heartbeat = Column(DateTime(timezone=True), default=func.now())
    
    # Metrics
    gpu_utilization = Column(Float, default=0.0)  # 0-100
    memory_utilization = Column(Float, default=0.0)  # 0-100
    network_latency_ms = Column(Float, default=0.0)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_nodes_status_active', 'status', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Node(id={self.id}, name={self.name}, status={self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": str(self.id),
            "name": self.name,
            "status": self.status,
            "gpu_model": self.gpu_model,
            "gpu_count": self.gpu_count,
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "location": {
                "country": self.country,
                "city": self.city,
                "latitude": self.latitude,
                "longitude": self.longitude,
            } if self.country or self.city else None,
            "metrics": {
                "gpu_utilization": self.gpu_utilization,
                "memory_utilization": self.memory_utilization,
                "network_latency_ms": self.network_latency_ms,
            },
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
