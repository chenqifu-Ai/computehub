# ComputeHub API v1 - Node Routes
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.models.node import Node
from src.api.v1.schemas.node import NodeCreate, NodeResponse, NodeUpdate
import uuid

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("/", response_model=NodeResponse, status_code=201)
def create_node(node_data: NodeCreate, db: Session = Depends(get_db)):
    """Create a new compute node."""
    new_node = Node(
        id=str(uuid.uuid4()),
        name=node_data.name,
        gpu_model=node_data.gpu_model,
        gpu_count=node_data.gpu_count,
        cpu_cores=node_data.cpu_cores,
        memory_gb=node_data.memory_gb,
        country=node_data.country,
        city=node_data.city,
        status="offline",
        is_active=True,
    )
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node


@router.get("/", response_model=list[NodeResponse])
def list_nodes(status: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all compute nodes."""
    query = db.query(Node)
    if status:
        query = query.filter(Node.status == status)
    nodes = query.offset(skip).limit(limit).all()
    return nodes


@router.get("/{node_id}", response_model=NodeResponse)
def get_node(node_id: str, db: Session = Depends(get_db)):
    """Get a node by ID."""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.put("/{node_id}", response_model=NodeResponse)
def update_node(node_id: str, node_data: NodeUpdate, db: Session = Depends(get_db)):
    """Update a node."""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    for key, value in node_data.model_dump(exclude_unset=True).items():
        setattr(node, key, value)
    
    db.commit()
    db.refresh(node)
    return node
