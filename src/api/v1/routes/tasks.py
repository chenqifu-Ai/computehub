# ComputeHub API v1 - Task Routes
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.models.task import Task
from src.api.v1.schemas.task import TaskCreate, TaskResponse
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(task_data: TaskCreate, user_id: str, db: Session = Depends(get_db)):
    """Submit a new compute task."""
    new_task = Task(
        id=str(uuid.uuid4()),
        user_id=user_id,
        framework=task_data.framework,
        gpu_required=task_data.gpu_required,
        duration_hours=task_data.duration_hours,
        memory_required_gb=task_data.memory_required_gb,
        code_url=task_data.code_url,
        data_url=task_data.data_url,
        parameters=task_data.parameters,
        status="PENDING",
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/", response_model=list[TaskResponse])
def list_tasks(status: str = None, user_id: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all tasks."""
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if user_id:
        query = query.filter(Task.user_id == user_id)
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get a task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, status: str, db: Session = Depends(get_db)):
    """Update task status."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = status
    db.commit()
    db.refresh(task)
    return task
