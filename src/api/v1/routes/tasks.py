"""任务路由 - 含 AI 调度"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.logging import logger
from src.models.user import User
from src.models.task import Task, TaskStatus, TaskPriority
from src.api.auth import get_current_user
from src.api.v1.schemas import TaskCreate, TaskResponse
from src.pipeline.pipeline import TaskPipeline
from src.kernel.scheduler import Scheduler
from src.kernel.ai_advisor import AISchedulerAdvisor

router = APIRouter(prefix="/tasks", tags=["任务"])

pipeline = TaskPipeline()
scheduler = Scheduler(strategy="least_connections")
ai_advisor = AISchedulerAdvisor(fallback_strategy="round_robin")


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """提交任务（AI 增强调度）"""

    # 1. Pipeline 净化
    payload_dict = data.payload or {}
    passed, cleaned, reason = pipeline.process(payload_dict)
    if not passed:
        raise HTTPException(status_code=400, detail=reason)

    # 2. AI 调度策略建议
    task_context = {
        "action": data.action,
        "framework": cleaned.get("framework", "python"),
        "gpu_required": cleaned.get("gpu_required", 1),
        "memory_required_gb": cleaned.get("memory_required_gb", 0),
    }
    ai_result = ai_advisor.get_recommendation(task_context)

    # 应用 AI 策略（如果有足够置信度）
    if ai_result["ai_used"] and ai_result["confidence"] >= 0.5:
        scheduler.load_balancer.set_strategy(ai_result["strategy"])
        logger.info(f"🎯 AI 调度: {ai_result['strategy']} (置信度={ai_result['confidence']:.2f})")
    else:
        logger.info(f"🎯 使用默认策略: {scheduler.load_balancer.strategy}")

    # 3. 创建任务
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

    # 4. 调度
    node_id = scheduler.schedule(task)
    if node_id:
        task.status = TaskStatus.QUEUED
        task.assigned_node = node_id
    else:
        task.status = TaskStatus.FAILED
        task.error = "No available nodes"

    db.add(task)
    db.commit()
    db.refresh(task)

    # 5. 异步执行（带 AI 决策上下文）
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
                "_strategy_used": ai_result["strategy"],
                "_ai_confidence": ai_result.get("confidence"),
            })
            logger.info(f"🚀 Task {task_id} dispatched to Celery (strategy={ai_result['strategy']})")
        except Exception as e:
            logger.warning(f"⚠️  Celery dispatch failed: {e}")

    return TaskResponse.model_validate(task)


@router.get("/", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tasks = db.query(Task).filter(Task.user_id == current_user.id).order_by(Task.created_at.desc()).all()
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.get("/ai/stats")
def ai_stats():
    """AI 调度状态"""
    return {
        "ai_advisor": ai_advisor.stats,
        "current_strategy": scheduler.load_balancer.strategy,
        "node_count": scheduler.load_balancer.node_count,
        "online_count": scheduler.load_balancer.online_count,
    }
