#!/usr/bin/env python3
"""
Node Agent - HTTP API Server
接收来自 ComputeHub Gateway 的任务并执行
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import asyncio
import subprocess
import os
import sys
import structlog
from datetime import datetime, timezone

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()

app = FastAPI(title="ComputeHub Node Agent")


class TaskExecuteRequest(BaseModel):
    """任务执行请求"""
    task_id: str
    framework: str
    code_url: Optional[str] = None
    data_url: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    gpu_required: int = 1
    memory_required_gb: int = 8


class TaskExecuteResponse(BaseModel):
    """任务执行响应"""
    task_id: str
    status: str  # executing/completed/failed
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_seconds: Optional[float] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress_percent: float
    eta_seconds: Optional[int] = None


# 当前执行的任务
current_task: Optional[Dict] = None


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "computehub-node-agent",
        "current_task": current_task["task_id"] if current_task else None,
    }


@app.post("/execute", response_model=TaskExecuteResponse)
async def execute_task(request: TaskExecuteRequest):
    """
    执行计算任务
    
    流程:
    1. 下载代码和数据
    2. 准备执行环境
    3. 运行任务
    4. 收集结果
    """
    global current_task
    
    logger.info("Received task execution request", task_id=request.task_id)
    
    if current_task and current_task["status"] == "executing":
        raise HTTPException(status_code=400, detail="Another task is already executing")
    
    # 记录任务开始
    current_task = {
        "task_id": request.task_id,
        "status": "executing",
        "started_at": datetime.now(timezone.utc),
        "framework": request.framework,
    }
    
    try:
        # TODO: 实现实际的任务执行逻辑
        # 1. 下载代码
        # if request.code_url:
        #     await download_code(request.code_url)
        
        # 2. 下载数据
        # if request.data_url:
        #     await download_data(request.data_url)
        
        # 3. 执行任务
        # result = await run_framework_task(request.framework, request.parameters)
        
        # 模拟执行（示例）
        await asyncio.sleep(2)  # 模拟执行延迟
        
        # 任务完成
        current_task["status"] = "completed"
        current_task["completed_at"] = datetime.now(timezone.utc)
        
        result_path = f"/results/{request.task_id}/output.tar.gz"
        
        return TaskExecuteResponse(
            task_id=request.task_id,
            status="completed",
            result_path=result_path,
            execution_time_seconds=2.0,
        )
        
    except Exception as e:
        logger.error("Task execution failed", error=str(e))
        current_task["status"] = "failed"
        current_task["error_message"] = str(e)
        
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务执行状态"""
    if not current_task or current_task["task_id"] != task_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 计算进度（示例）
    progress = 100.0 if current_task["status"] == "completed" else 50.0
    
    return TaskStatusResponse(
        task_id=task_id,
        status=current_task["status"],
        progress_percent=progress,
        eta_seconds=0 if current_task["status"] == "completed" else 300,
    )


@app.get("/metrics")
async def get_metrics():
    """获取节点性能指标"""
    import psutil
    
    # 尝试获取 GPU 信息
    gpu_info = {}
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_info = {
            "gpu_name": pynvml.nvmlDeviceGetName(handle),
            "gpu_utilization": pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
            "gpu_temperature": pynvml.nvmlDeviceGetTemperature(handle, 0),
            "memory_used": pynvml.nvmlDeviceGetMemoryInfo(handle).used,
            "memory_total": pynvml.nvmlDeviceGetMemoryInfo(handle).total,
        }
        pynvml.nvmlShutdown()
    except Exception:
        gpu_info = {"available": False}
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "gpu": gpu_info,
        "current_task": current_task["task_id"] if current_task else None,
    }


if __name__ == "__main__":
    logger.info("Starting ComputeHub Node Agent API")
    uvicorn.run(app, host="0.0.0.0", port=8080)
