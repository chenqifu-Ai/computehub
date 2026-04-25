"""节点路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from src.core.database import get_db
from src.models.user import User
from src.models.node import Node, NodeStatus
from src.api.auth import get_current_user
from src.api.v1.schemas import NodeRegister, NodeResponse, NodeStatusUpdate

router = APIRouter(prefix="/nodes", tags=["节点"])


@router.post("/register", response_model=NodeResponse)
def register_node(data: NodeRegister, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """注册节点"""
    existing = db.query(Node).filter(Node.id == data.node_id).first()
    if existing:
        existing.name = data.name
        existing.gpu_count = data.gpu_count
        existing.memory_gb = data.memory_gb
        existing.cpu_cores = data.cpu_cores
        existing.status = NodeStatus.ONLINE
        existing.last_heartbeat = datetime.now(timezone.utc)
    else:
        node = Node(
            id=data.node_id,
            name=data.name,
            status=NodeStatus.ONLINE,
            gpu_count=data.gpu_count,
            memory_gb=data.memory_gb,
            cpu_cores=data.cpu_cores,
            owner_id=current_user.id,
            last_heartbeat=datetime.now(timezone.utc),
        )
        db.add(node)
    db.commit()
    db.refresh(existing or node)
    return NodeResponse.model_validate(existing or node)


@router.get("/", response_model=list[NodeResponse])
def list_nodes(db: Session = Depends(get_db)):
    """节点列表"""
    return [NodeResponse.model_validate(n) for n in db.query(Node).all()]


@router.post("/heartbeat")
def heartbeat(data: NodeStatusUpdate, db: Session = Depends(get_db)):
    """节点心跳"""
    node = db.query(Node).filter(Node.id == data.node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.last_heartbeat = datetime.now(timezone.utc)
    node.status = NodeStatus.ONLINE
    if data.gpu_utilization is not None:
        node.gpu_utilization = data.gpu_utilization
    if data.memory_utilization is not None:
        node.memory_utilization = data.memory_utilization
    if data.cpu_utilization is not None:
        node.cpu_utilization = data.cpu_utilization
    if data.queue_depth is not None:
        node.queue_depth = data.queue_depth
    db.commit()
    return {"status": "ok"}
