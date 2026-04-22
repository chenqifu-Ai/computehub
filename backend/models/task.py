"""
Task Model - Represents compute tasks
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.base import Base
import uuid
import enum


class TaskStatus(enum.Enum):
    """Task status enumeration"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    """Compute task model"""
    
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, index=True)
    
    # Assigned node
    node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=True)
    
    # Task specifications
    framework = Column(String(50))  # pytorch/tensorflow/jax
    gpu_required = Column(Integer, default=1)
    duration_hours = Column(Integer, default=1)
    memory_required_gb = Column(Integer, default=8)
    
    # Task content
    code_url = Column(Text)  # URL to code repository
    data_url = Column(Text)  # URL to input data
    parameters = Column(Text)  # JSON string of parameters
    
    # Results
    result_path = Column(Text)  # Path to output results
    error_message = Column(Text)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Billing
    gpu_hours_consumed = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)
    
    # Relationships
    node = relationship("Node", backref="tasks")
    
    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, node_id={self.node_id})>"
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "status": self.status.value,
            "node_id": str(self.node_id) if self.node_id else None,
            "framework": self.framework,
            "gpu_required": self.gpu_required,
            "duration_hours": self.duration_hours,
            "result_path": self.result_path,
            "error_message": self.error_message,
            "gpu_hours_consumed": self.gpu_hours_consumed,
            "cost_usd": self.cost_usd,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
