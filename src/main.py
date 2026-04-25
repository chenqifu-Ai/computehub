"""ComputeHub v2.0 MVP - FastAPI 入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core import config
from src.core.logging import logger
from src.api.v1.router import router as v1_router

app = FastAPI(
    title="ComputeHub v2.0 MVP",
    description="分布式算力平台 - 简化版",
    version="2.0.0-mvp",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "service": "ComputeHub",
        "version": "2.0.0-mvp",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# 启动时初始化
@app.on_event("startup")
def startup():
    config.load()
    logger.info("✅ ComputeHub MVP started")

    # 创建表
    from src.core.database import engine, Base
    import src.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
