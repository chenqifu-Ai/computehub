from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# 假设已经在 api/rest_api.py 中定义
from api.rest_api import get_db_conn

app = FastAPI(title="ComputeHub-Admin-API")

class AuditRequest(BaseModel):
    node_id: str
    task_id: str

@app.get("/api/v1/audit/physical-proof")
async def get_physical_proof(node_id: str, task_id: str):
    """
    物理审计接口：直接从时序数据库提取任务期间的物理指纹证据
    """
    conn = get_db_conn()
    if not conn: raise HTTPException(status_code=500, detail="DB unavailable")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 查询该节点在任务期间的所有心跳记录，作为审计凭证
            cur.execute(
                "SELECT timestamp, temperature, utilization, power_draw FROM node_heartbeats "
                "WHERE node_id = %s ORDER BY timestamp ASC", (node_id,)
            )
            proofs = cur.fetchall()
        return {"task_id": task_id, "node_id": node_id, "proofs": proofs}
    finally:
        conn.close()
