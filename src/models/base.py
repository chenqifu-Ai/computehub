# ComputeHub Models - Base model
from sqlalchemy import Column, DateTime, func
from src.core.database import Base


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
