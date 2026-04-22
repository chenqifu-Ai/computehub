"""
User Model - Platform users
"""

from sqlalchemy import Column, String, DateTime, Boolean, Float
from sqlalchemy.sql import func
from backend.models.base import Base
import uuid


class User(Base):
    """Platform user model"""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    
    # Security
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Profile
    full_name = Column(String(255))
    company = Column(String(255))
    
    # Billing
    balance_usd = Column(Float, default=0.0)
    total_spent_usd = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "company": self.company,
            "is_active": self.is_active,
            "balance_usd": self.balance_usd,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
