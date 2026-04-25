"""数据库连接 - SQLAlchemy"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.core import config

# 创建引擎
engine = create_engine(
    config.database_url,
    echo=False,
    pool_pre_ping=True,
)

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM Base
Base = declarative_base()


def get_db():
    """FastAPI 依赖 - 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
