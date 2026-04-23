# ComputeHub Core - Database
# SQLAlchemy engine and session management

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.core.config import config

engine = create_engine(
    config.database_url,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI - provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
