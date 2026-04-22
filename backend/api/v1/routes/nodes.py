"""
Node API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from backend.models.node import Node
from backend.models.base import async_session_maker
from backend.api.v1.schemas.node import (
    NodeRegister,
    NodeHeartbeat,
)
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


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_node(node_data: NodeRegister, db=Depends(get_db)):
    """Register a new compute node"""
    logger.info("Registering new node", name=node_data.name)
    
    node = Node(
        name=node_data.name,
        gpu_model=node_data.gpu_model,
        gpu_count=node_data.gpu_count,
        cpu_cores=node_data.cpu_cores,
        memory_gb=node_data.memory_gb,
        country=node_data.country,
        city=node_data.city,
        latitude=node_data.latitude,
        longitude=node_data.longitude,
        status="online",
        last_heartbeat=datetime.now(timezone.utc),
    )
    
    db.add(node)
    await db.commit()
    await db.refresh(node)
    
    logger.info("Node registered successfully", node_id=str(node.id))
    return node.to_dict()


@router.get("/", response_model=dict)
async def list_nodes(
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db)
):
    """List all compute nodes"""
    query = select(Node)
    
    if status:
        query = query.where(Node.status == status)
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    nodes = result.scalars().all()
    
    return {
        "nodes": [n.to_dict() for n in nodes],
        "total": len(nodes)
    }


@router.get("/{node_id}", response_model=dict)
async def get_node(node_id: str, db=Depends(get_db)):
    """Get a specific node by ID"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")
    
    result = await db.execute(select(Node).where(Node.id == node_uuid))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return node.to_dict()


@router.post("/{node_id}/heartbeat", response_model=dict)
async def node_heartbeat(
    node_id: str,
    heartbeat: NodeHeartbeat,
    db=Depends(get_db)
):
    """Receive heartbeat from a node"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")
    
    logger.debug("Received heartbeat", node_id=node_id)
    
    result = await db.execute(select(Node).where(Node.id == node_uuid))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.gpu_utilization = heartbeat.gpu_utilization
    node.memory_utilization = heartbeat.memory_utilization
    node.network_latency_ms = heartbeat.network_latency_ms
    node.last_heartbeat = datetime.now(timezone.utc)
    
    if node.status == "offline":
        node.status = "online"
    
    await db.commit()
    await db.refresh(node)
    
    return node.to_dict()


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: str, db=Depends(get_db)):
    """Delete a node (deactivate)"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")
    
    result = await db.execute(select(Node).where(Node.id == node_uuid))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.is_active = False
    node.status = "offline"
    
    await db.commit()
    
    logger.info("Node deleted", node_id=node_id)


@router.post("/{node_id}/maintenance", response_model=dict)
async def set_maintenance(node_id: str, db=Depends(get_db)):
    """Set node to maintenance mode"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")
    
    result = await db.execute(select(Node).where(Node.id == node_uuid))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.status = "maintenance"
    await db.commit()
    await db.refresh(node)
    
    return node.to_dict()
