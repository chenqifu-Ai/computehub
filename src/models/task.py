"""Task 模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, func, Enum as SAEnum
import enum

from src.core.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True)  # task_id
    user_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False)
    payload = Column(Text, default="{}")  # JSON string
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(SAEnum(TaskPriority), default=TaskPriority.MEDIUM)
    assigned_node = Column(String(64), nullable=True)
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
