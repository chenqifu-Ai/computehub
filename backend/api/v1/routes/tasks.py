"""
Task API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import uuid

from backend.models.task import Task, TaskStatus
from backend.models.base import get_db
from backend.api.v1.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskListResponse,
)
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = get_db,
    # TODO: Add user authentication
    # current_user = Depends(get_current_user)
):
    """
    Create a new compute task
    
    Task will be queued and scheduled to an available node
    """
    logger.info("Creating new task", framework=task_data.framework)
    
    # Create task (user_id is temporary placeholder)
    task = Task(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # TODO: Replace with auth
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
    
    logger.info("Task created successfully", task_id=str(task.id))
    
    # TODO: Trigger Celery task to schedule this task
    # from backend.workers.tasks import schedule_task
    # schedule_task.delay(str(task.id))
    
    return task


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = get_db
):
    """
    List all tasks
    
    Optional status filter: pending, executing, completed, failed, etc.
    """
    query = select(Task).offset(offset).limit(limit)
    
    if status:
        query = query.where(Task.status == TaskStatus(status))
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=len(tasks)
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = get_db):
    """
    Get a specific task by ID
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str, db: AsyncSession = get_db):
    """
    Cancel a pending or executing task
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in status {task.status.value}")
    
    task.status = TaskStatus.CANCELLED
    await db.commit()
    await db.refresh(task)
    
    logger.info("Task cancelled", task_id=task_id)
    return task
