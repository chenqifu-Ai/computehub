#!/usr/bin/env python3
"""
ComputeHub Node Agent
Runs on compute nodes to register with gateway and execute tasks
"""

import argparse
import asyncio
import httpx
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
import psutil

# Try to import pynvml for GPU monitoring
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    print("Warning: pynvml not available, GPU monitoring disabled")

try:
    from ping3 import ping
    PING3_AVAILABLE = True
except ImportError:
    PING3_AVAILABLE = False

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()


class NodeAgent:
    """Node agent that communicates with ComputeHub gateway"""
    
    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        node_name: Optional[str] = None,
        heartbeat_interval: int = 30,
    ):
        self.gateway_url = gateway_url.rstrip('/')
        self.node_name = node_name or f"node-{uuid.uuid4().hex[:8]}"
        self.heartbeat_interval = heartbeat_interval
        self.node_id: Optional[str] = None
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
    
    def get_hardware_info(self) -> dict:
        """Collect hardware information"""
        info = {
            "cpu_cores": psutil.cpu_count(logical=True),
            "memory_gb": psutil.virtual_memory().total // (1024**3),
        }
        
        # GPU info
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(gpu_name, bytes):
                        gpu_name = gpu_name.decode('utf-8')
                    info["gpu_model"] = gpu_name
                    info["gpu_count"] = device_count
                pynvml.nvmlShutdown()
            except Exception as e:
                logger.warning("Failed to get GPU info", error=str(e))
        
        return info
    
    def get_metrics(self) -> dict:
        """Collect current metrics"""
        metrics = {
            "cpu_utilization": psutil.cpu_percent(interval=0.1),
            "memory_utilization": psutil.virtual_memory().percent,
        }
        
        # GPU metrics
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    metrics["gpu_utilization"] = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    metrics["gpu_temperature"] = pynvml.nvmlDeviceGetTemperature(handle, 0)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    metrics["available_memory_gb"] = mem_info.free / (1024**3)
                pynvml.nvmlShutdown()
            except Exception as e:
                logger.warning("Failed to get GPU metrics", error=str(e))
        
        # Network latency
        if PING3_AVAILABLE:
            try:
                latency = ping(f"{self.gateway_url.replace('http://', '').replace('https://', '').split('/')[0]}")
                if latency:
                    metrics["network_latency_ms"] = latency * 1000
            except Exception:
                pass
        
        return metrics
    
    async def register(self) -> bool:
        """Register this node with the gateway"""
        logger.info("Registering node with gateway", gateway=self.gateway_url)
        
        hw_info = self.get_hardware_info()
        
        payload = {
            "name": self.node_name,
            **hw_info,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gateway_url}/api/v1/nodes/register",
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    self.node_id = data["id"]
                    logger.info("Node registered successfully", node_id=self.node_id)
                    return True
                else:
                    logger.error("Registration failed", status=response.status_code, body=response.text)
                    return False
                    
        except Exception as e:
            logger.error("Registration failed", error=str(e))
            return False
    
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to gateway"""
        if not self.node_id:
            logger.warning("Cannot send heartbeat: node not registered")
            return False
        
        metrics = self.get_metrics()
        
        payload = {
            "gpu_utilization": metrics.get("gpu_utilization", 0.0),
            "memory_utilization": metrics.get("memory_utilization", 0.0),
            "network_latency_ms": metrics.get("network_latency_ms", 0.0),
            "gpu_temperature": metrics.get("gpu_temperature"),
            "available_memory_gb": metrics.get("available_memory_gb"),
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gateway_url}/api/v1/nodes/{self.node_id}/heartbeat",
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.debug("Heartbeat sent", **metrics)
                    return True
                else:
                    logger.error("Heartbeat failed", status=response.status_code)
                    return False
                    
        except Exception as e:
            logger.error("Heartbeat failed", error=str(e))
            return False
    
    async def run(self):
        """Main agent loop"""
        logger.info("Starting node agent", name=self.node_name)
        self.running = True
        
        # Register
        if not await self.register():
            logger.error("Failed to register, exiting")
            return
        
        # Heartbeat loop
        while self.running:
            try:
                await self.send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat loop error", error=str(e))
                await asyncio.sleep(self.heartbeat_interval)
        
        logger.info("Node agent stopped")
    
    def stop(self):
        """Stop the agent"""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="ComputeHub Node Agent")
    parser.add_argument("--gateway", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--name", help="Node name (auto-generated if not provided)")
    parser.add_argument("--heartbeat-interval", type=int, default=30, help="Heartbeat interval in seconds")
    args = parser.parse_args()
    
    agent = NodeAgent(
        gateway_url=args.gateway,
        node_name=args.name,
        heartbeat_interval=args.heartbeat_interval,
    )
    
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        agent.stop()


if __name__ == "__main__":
    main()
