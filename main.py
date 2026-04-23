#!/usr/bin/env python3
# ComputeHub v2.0 - Main Application Entry Point
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import config
from src.core.logging import get_logger
from src.core.database import engine, Base
from src.api.v1.router import api_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ComputeHub",
    description="Distributed Compute Platform",
    version="2.0.0",
    docs_url=config.data.get("gateway", {}).get("docs_url", "/docs"),
    redoc_url=config.data.get("gateway", {}).get("redoc_url", "/redoc"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"success": True, "message": "ComputeHub v2.0 Healthy"}

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

app.include_router(api_router)

@app.get("/")
def root():
    return {
        "name": "ComputeHub",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "status": "/api/status",
    }

if __name__ == "__main__":
    import uvicorn
    port = config.gateway_port
    host = config.gateway_host
    logger = get_logger("computehub", "INFO")
    logger.info(f"🚀 Starting ComputeHub v2.0 on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
    )
