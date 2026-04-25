"""API v1 路由聚合"""
from fastapi import APIRouter

from src.api.v1.routes import auth, users, nodes, tasks

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(nodes.router)
router.include_router(tasks.router)
