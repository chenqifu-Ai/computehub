"""
Unit tests for Node API
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ComputeHub API"
    assert data["version"] == "2.0.0"


def test_register_node():
    """Test node registration"""
    node_data = {
        "name": "test-node-1",
        "gpu_model": "RTX 4090",
        "gpu_count": 1,
        "cpu_cores": 8,
        "memory_gb": 32,
        "country": "China",
        "city": "Beijing",
        "latitude": 39.9042,
        "longitude": 116.4074,
    }
    
    response = client.post("/api/v1/nodes/register", json=node_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-node-1"
    assert data["status"] == "online"
    assert "id" in data
    return data["id"]


def test_list_nodes():
    """Test listing nodes"""
    response = client.get("/api/v1/nodes/")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "total" in data


def test_node_heartbeat():
    """Test node heartbeat"""
    # First register a node
    node_data = {
        "name": "test-node-heartbeat",
        "gpu_count": 1,
        "cpu_cores": 4,
        "memory_gb": 16,
    }
    response = client.post("/api/v1/nodes/register", json=node_data)
    node_id = response.json()["id"]
    
    # Send heartbeat
    heartbeat_data = {
        "gpu_utilization": 45.5,
        "memory_utilization": 62.3,
        "network_latency_ms": 25.7,
    }
    
    response = client.post(f"/api/v1/nodes/{node_id}/heartbeat", json=heartbeat_data)
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["gpu_utilization"] == 45.5
