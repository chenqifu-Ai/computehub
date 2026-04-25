"""任务路由 - 含 Celery 异步调度"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.config import config
from src.models.user import User
from src.models.task import Task, TaskStatus, TaskPriority
from src.api.auth import get_current_user
from src.api.v1.schemas import TaskCreate, TaskResponse
from src.pipeline.pipeline import TaskPipeline
from src.kernel.scheduler import Scheduler

router = APIRouter(prefix="/tasks", tags=["任务"])

# 全局实例
pipeline = TaskPipeline()
scheduler = Scheduler(strategy="least_connections")


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """提交任务"""
    # 1. Pipeline 净化和校验
    payload_dict = data.payload or {}
    passed, cleaned, reason = pipeline.process(payload_dict)
    if not passed:
        raise HTTPException(status_code=400, detail=reason)

    # 2. 选择节点
    task_id = str(uuid.uuid4())[:8]
    priority = TaskPriority(data.priority.upper()) if data.priority.upper() in TaskPriority.__members__ else TaskPriority.MEDIUM

    task = Task(
        id=task_id,
        user_id=current_user.id,
        action=data.action,
        payload=json.dumps(cleaned),
        status=TaskStatus.PENDING,
        priority=priority,
    )

    # 3. 调度
    node_id = scheduler.schedule(task)
    if node_id:
        task.status = TaskStatus.QUEUED
        task.assigned_node = node_id
    else:
        task.status = TaskStatus.FAILED
        task.error = "No available nodes"

    db.add(task)
    db.commit()

    # 4. 异步执行（如果有可用节点和 Celery）
    if node_id:
        try:
            from src.workers.task_worker import execute_task
            execute_task.delay({
                "id": task_id,
                "action": data.action,
                "payload": cleaned,
                "parameters": cleaned.get("parameters", ""),
                "framework": cleaned.get("framework", "python"),
                "code_url": cleaned.get("code_url", ""),
            })
        except Exception as e:
            # Celery 不可用，任务已排队，稍后手动运行
            pass

    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.get("/", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """任务列表"""
    tasks = db.query(Task).filter(Task.user_id == current_user.id).order_by(Task.created_at.desc()).all()
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    """任务详情"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)
