"""任务路由"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.user import User
from src.models.task import Task, TaskStatus, TaskPriority
from src.api.auth import get_current_user
from src.api.v1.schemas import TaskCreate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["任务"])


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """提交任务"""
    task_id = str(uuid.uuid4())[:8]
    priority = TaskPriority(data.priority.upper()) if data.priority.upper() in TaskPriority.__members__ else TaskPriority.MEDIUM

    task = Task(
        id=task_id,
        user_id=current_user.id,
        action=data.action,
        payload=str(data.payload),
        status=TaskStatus.QUEUED,
        priority=priority,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.get("/", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """任务列表（仅自己的任务）"""
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
