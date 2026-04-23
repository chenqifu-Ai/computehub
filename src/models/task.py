# ComputeHub Models - Task
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base
from src.models.base import TimestampMixin


class Task(TimestampMixin, Base):
    """Task model - represents a compute job submitted to the platform."""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)  # UUID as string
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(9), default="PENDING")  # PENDING, SCHEDULED, RUNNING, COMPLETED, FAILED, CANCELLED
    node_id = Column(String, ForeignKey("nodes.id"))
    framework = Column(String(50), default="pytorch")
    gpu_required = Column(Integer, default=1)
    duration_hours = Column(Integer, default=1)
    memory_required_gb = Column(Integer, default=8)
    code_url = Column(Text)
    data_url = Column(Text)
    parameters = Column(Text)
    result_path = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    gpu_hours_consumed = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="tasks")
    node = relationship("Node", back_populates="tasks")
