"""
ComputeHub Configuration
Using Pydantic Settings for type-safe configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "ComputeHub"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # Database (SQLite for development, PostgreSQL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./computehub.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Node Settings
    NODE_HEARTBEAT_INTERVAL: int = 30  # seconds
    NODE_TIMEOUT: int = 90  # seconds (3x heartbeat)
    
    # Scheduler
    SCHEDULER_ENABLED: bool = True
    MAX_TASK_RETRIES: int = 3
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
