#!/usr/bin/env python3
# ComputeHub v2.0 - Main Application Entry Point
# Inherited from OpenPC System architecture pattern

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import config
from src.core.logging import get_logger
from src.core.database import engine, Base
from src.models.user import User
from src.models.node import Node
from src.models.task import Task
from src.api.v1.router import api_router
from src.kernel.scheduler import TaskScheduler

# Setup logging (OpenPC System pattern)
logger = get_logger("computehub", config.data.get("logging", {}).get("level", "INFO"))

# Create tables (idempotent - won't fail if they exist)
Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(
    title="ComputeHub",
    description="Distributed Compute Platform",
    version="2.0.0",
    docs_url=config.data.get("gateway", {}).get("docs_url", "/docs"),
    redoc_url=config.data.get("gateway", {}).get("redoc_url", "/redoc"),
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (OpenPC System pattern)
@app.get("/api/health")
def health_check():
    return {"success": True, "message": "ComputeHub v2.0 Healthy"}

# Status endpoint
@app.get("/api/status")
def status():
    return {
        "success": True,
        "data": {
            "version": "2.0.0",
            "status": "RUNNING",
            "database": "connected",
            "tables": ["users", "nodes", "tasks"],
        }
    }

# Include API router
app.include_router(api_router)

# Root endpoint
@app.get("/")
def root():
    return {
        "name": "ComputeHub",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "status": "/api/status",
    }

# Global scheduler instance
scheduler: TaskScheduler = None


@app.on_event("startup")
async def startup_event():
    """Start the scheduler on application startup."""
    global scheduler
    scheduler = TaskScheduler(
        strategy=config.data.get("load_balancer", {}).get("strategy", "least_utilization"),
        queue_size=config.data.get("kernel", {}).get("queue_size", 1000),
    )
    scheduler.start()
    logger.info("✅ Scheduler initialized and started")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler on application shutdown."""
    global scheduler
    if scheduler:
        scheduler.stop()
        logger.info("⏹️  Scheduler stopped")


if __name__ == "__main__":
    import uvicorn
    port = config.gateway_port
    host = config.gateway_host
    logger.info(f"🚀 Starting ComputeHub v2.0 on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
    )
