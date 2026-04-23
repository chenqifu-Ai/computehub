# ComputeHub API v1 - Main Router
from fastapi import APIRouter
from src.api.v1.routes import users, nodes, tasks

api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(nodes.router)
api_router.include_router(tasks.router)
