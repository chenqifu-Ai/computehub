"""
Task API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import uuid

from backend.models.task import Task, TaskStatus
from backend.models.base import async_session_maker
from backend.api.v1.schemas.task import (
    TaskCreate,
)
from backend.services.scheduler import SmartScheduler
import structlog

logger = structlog.get_logger()

router = APIRouter()


async def get_db():
    """Database dependency"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db = Depends(get_db),
):
    """Create a new compute task and schedule it"""
    logger.info("Creating new task", framework=task_data.framework)
    
    task = Task(
        user_id="00000000-0000-0000-0000-000000000000",
        status=TaskStatus.PENDING,
        framework=task_data.framework,
        gpu_required=task_data.gpu_required,
        duration_hours=task_data.duration_hours,
        memory_required_gb=task_data.memory_required_gb,
        code_url=task_data.code_url,
        data_url=task_data.data_url,
        parameters=str(task_data.parameters) if task_data.parameters else None,
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # 智能调度：自动分配节点
    scheduled = await SmartScheduler.schedule_task(db, task)
    
    if scheduled:
        logger.info("Task created and scheduled", task_id=str(task.id))
    else:
        logger.warning("Task created but scheduling failed", task_id=str(task.id))
    
    await db.refresh(task)
    return task.to_dict()


@router.get("", response_model=dict)
async def list_tasks(
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    db = Depends(get_db)
):
    """List all tasks"""
    query = select(Task).offset(offset).limit(limit)
    
    if status:
        query = query.where(Task.status == TaskStatus(status))
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks)
    }


@router.get("/{task_id}", response_model=dict)
async def get_task(task_id: str, db = Depends(get_db)):
    """Get a specific task by ID"""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task.to_dict()


@router.post("/{task_id}/cancel", response_model=dict)
async def cancel_task(task_id: str, db = Depends(get_db)):
    """Cancel a pending or executing task"""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in status {task.status.value}")
    
    task.status = TaskStatus.CANCELLED
    await db.commit()
    await db.refresh(task)
    
    logger.info("Task cancelled", task_id=task_id)
    return task.to_dict()
