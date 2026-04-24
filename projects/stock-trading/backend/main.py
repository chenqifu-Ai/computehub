"""
股票交易软件 - 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入路由
from routes import auth, market, strategy, trading, account
from database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时初始化数据库
    print("🚀 股票交易系统启动中...")
    print("📊 数据库已初始化")
    yield
    # 关闭时清理资源
    print("👋 股票交易系统关闭")

app = FastAPI(
    title="股票交易API",
    description="量化交易软件后端API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "股票交易API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "认证": "/api/v1/auth",
            "行情": "/api/v1/market",
            "策略": "/api/v1/strategies",
            "交易": "/api/v1/trading",
            "账户": "/api/v1/account"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(market.router, prefix="/api/v1/market", tags=["行情"])
app.include_router(strategy.router, prefix="/api/v1/strategies", tags=["策略"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["交易"])
app.include_router(account.router, prefix="/api/v1/account", tags=["账户"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)