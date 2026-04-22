"""
Node API Routes
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timezone

from backend.models.node import Node
from backend.models.base import get_db
from backend.api.v1.schemas.node import (
    NodeRegister,
    NodeHeartbeat,
    NodeResponse,
    NodeListResponse,
)
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.post("/register", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def register_node(node_data: NodeRegister, db: AsyncSession = get_db):
    """
    Register a new compute node
    
    Returns the registered node with assigned ID
    """
    logger.info("Registering new node", name=node_data.name)
    
    # Create new node
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
    return node


@router.get("/", response_model=NodeListResponse)
async def list_nodes(
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = get_db
):
    """
    List all compute nodes
    
    Optional status filter: online, offline, maintenance
    """
    query = select(Node)
    
    if status:
        query = query.where(Node.status == status)
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    nodes = result.scalars().all()
    
    # Get total count
    count_query = select(Node)
    if status:
        count_query = count_query.where(Node.status == status)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return NodeListResponse(
        nodes=[NodeResponse.model_validate(n) for n in nodes],
        total=total
    )


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: str, db: AsyncSession = get_db):
    """
    Get a specific node by ID
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return node


@router.post("/{node_id}/heartbeat", response_model=NodeResponse)
async def node_heartbeat(
    node_id: str,
    heartbeat: NodeHeartbeat,
    db: AsyncSession = get_db
):
    """
    Receive heartbeat from a node
    
    Updates node metrics and last heartbeat timestamp
    """
    logger.debug("Received heartbeat", node_id=node_id)
    
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Update node metrics
    node.gpu_utilization = heartbeat.gpu_utilization
    node.memory_utilization = heartbeat.memory_utilization
    node.network_latency_ms = heartbeat.network_latency_ms
    node.last_heartbeat = datetime.now(timezone.utc)
    
    # Auto-set status to online if heartbeat received
    if node.status == "offline":
        node.status = "online"
    
    await db.commit()
    await db.refresh(node)
    
    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: str, db: AsyncSession = get_db):
    """
    Delete a node (deactivate)
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Soft delete - mark as inactive
    node.is_active = False
    node.status = "offline"
    
    await db.commit()
    
    logger.info("Node deleted", node_id=node_id)


@router.post("/{node_id}/maintenance", response_model=NodeResponse)
async def set_maintenance(node_id: str, db: AsyncSession = get_db):
    """
    Set node to maintenance mode
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.status = "maintenance"
    await db.commit()
    await db.refresh(node)
    
    return node
