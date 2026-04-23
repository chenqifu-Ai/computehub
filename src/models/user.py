# ComputeHub Models - User
from sqlalchemy import Column, String, Boolean, Float, DateTime, func
from sqlalchemy.orm import relationship
from src.core.database import Base
from src.models.base import TimestampMixin


class User(TimestampMixin, Base):
    """User model - represents a ComputeHub platform user."""
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # UUID as string
    email = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    full_name = Column(String(255))
    company = Column(String(255))
    balance_usd = Column(Float, default=0.0)
    total_spent_usd = Column(Float, default=0.0)
    last_login = Column(DateTime)
    
    # Relationships
    tasks = relationship("Task", back_populates="user")
