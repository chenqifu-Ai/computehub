"""
ComputeHub - Main Application Entry Point
FastAPI Application with lifecycle management
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from backend.core.config import settings
from backend.api.v1.routes import nodes, tasks, users, cluster
from backend.models import base

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting ComputeHub API...")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"Redis: {settings.REDIS_URL}")
    
    # Initialize database tables
    await base.create_db_tables()
    logger.info("Database tables initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ComputeHub API...")


# Create FastAPI application
app = FastAPI(
    title="ComputeHub API",
    description="Distributed Computing Power Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(nodes.router, prefix="/api/v1/nodes", tags=["nodes"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(cluster.router, prefix="/api/v1/cluster", tags=["cluster"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "computehub-api"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ComputeHub API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
