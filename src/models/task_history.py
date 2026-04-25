"""任务执行历史记录模型 - AI 调度数据基础"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, func

from src.core.database import Base


class TaskExecutionHistory(Base):
    """记录每次任务的执行特征和结果，用于 AI 调度分析"""
    __tablename__ = "task_execution_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)

    # 任务特征（供 AI 分析）
    action = Column(String(50), nullable=False)
    payload_summary = Column(String(255), default="")  # 任务类型的摘要
    framework = Column(String(50), default="python")
    gpu_required = Column(Integer, default=1)
    memory_required_gb = Column(Integer, default=0)
    input_size_chars = Column(Integer, default=0)  # 输入大小

    # 调度决策
    strategy_used = Column(String(50), nullable=False)  # AI 建议/least_connections/round_robin
    ai_confidence = Column(Float, nullable=True)  # AI 建议的置信度
    scheduled_node = Column(String(64), nullable=True)

    # 执行结果
    status = Column(String(20), nullable=False)  # COMPLETED/FAILED/TIMEOUT
    duration_ms = Column(Float, nullable=True)
    exit_code = Column(Integer, nullable=True)
    node_utilization_before = Column(Float, nullable=True)  # 调度前节点利用率

    created_at = Column(DateTime, server_default=func.now())
