"""
智能调度器 - 负责将任务分配到最优节点
"""

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional, List
import structlog

from backend.models.node import Node
from backend.models.task import Task, TaskStatus

logger = structlog.get_logger()


class SmartScheduler:
    """智能调度器"""
    
    @staticmethod
    async def find_best_node(
        db: AsyncSession,
        gpu_required: int = 1,
        memory_required_gb: int = 8,
        framework: str = None
    ) -> Optional[Node]:
        """
        根据任务需求找到最优节点
        
        调度策略:
        1. 只选择在线且活跃的节点
        2. GPU 数量满足要求
        3. 内存满足要求
        4. 优先选择 GPU 利用率低的节点（负载均衡）
        5. 优先选择网络延迟低的节点
        """
        logger.info("Finding best node for task", 
                   gpu_required=gpu_required, 
                   memory_required_gb=memory_required_gb)
        
        # 查询符合条件的节点
        query = select(Node).where(
            and_(
                Node.status == "online",
                Node.is_active == True,
                Node.gpu_count >= gpu_required,
                Node.memory_gb >= memory_required_gb,
            )
        )
        
        result = await db.execute(query)
        candidates = result.scalars().all()
        
        if not candidates:
            logger.warning("No available nodes found")
            return None
        
        # 评分算法：选择最优节点
        # 分数 = (100 - gpu_utilization) * 0.6 + (100 - network_latency) * 0.4
        best_node = None
        best_score = -1
        
        for node in candidates:
            # GPU 利用率分数（越低越好）
            gpu_score = 100 - node.gpu_utilization
            
            # 网络延迟分数（越低越好，假设>100ms 为 0 分）
            latency_score = max(0, 100 - node.network_latency_ms)
            
            # 综合评分
            score = gpu_score * 0.6 + latency_score * 0.4
            
            logger.debug(f"Node {node.name} score: {score:.2f}", 
                        gpu_score=gpu_score, 
                        latency_score=latency_score)
            
            if score > best_score:
                best_score = score
                best_node = node
        
        if best_node:
            logger.info("Best node selected", 
                       node_id=str(best_node.id), 
                       node_name=best_node.name,
                       score=best_score)
        
        return best_node
    
    @staticmethod
    async def schedule_task(db: AsyncSession, task: Task) -> bool:
        """
        调度任务到节点
        
        流程:
        1. 找到最优节点
        2. 更新任务状态和节点关联
        3. 触发任务执行
        
        返回：是否调度成功
        """
        logger.info("Scheduling task", task_id=str(task.id))
        
        # 找到最优节点
        best_node = await SmartScheduler.find_best_node(
            db,
            gpu_required=task.gpu_required,
            memory_required_gb=task.memory_required_gb,
            framework=task.framework
        )
        
        if not best_node:
            logger.warning("No suitable node found for task", task_id=str(task.id))
            task.status = TaskStatus.FAILED
            task.error_message = "No available nodes matching requirements"
            await db.commit()
            return False
        
        # 更新任务状态
        task.status = TaskStatus.SCHEDULED
        task.node_id = best_node.id
        task.started_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info("Task scheduled successfully", 
                   task_id=str(task.id),
                   node_id=str(best_node.id),
                   node_name=best_node.name)
        
        # TODO: 触发 Celery 任务执行
        # from backend.workers.tasks import execute_task
        # execute_task.delay(str(task.id), str(best_node.id))
        
        return True
    
    @staticmethod
    async def get_cluster_stats(db: AsyncSession) -> dict:
        """获取集群统计信息"""
        # 总节点数
        total_result = await db.execute(select(Node))
        total_nodes = len(total_result.scalars().all())
        
        # 在线节点数
        online_result = await db.execute(
            select(Node).where(Node.status == "online")
        )
        online_nodes = len(online_result.scalars().all())
        
        # 总 GPU 数
        gpu_result = await db.execute(select(Node))
        total_gpus = sum(n.gpu_count for n in gpu_result.scalars().all())
        
        # 平均 GPU 利用率
        avg_gpu_util = sum(n.gpu_utilization for n in gpu_result.scalars().all()) / max(1, total_nodes)
        
        return {
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "offline_nodes": total_nodes - online_nodes,
            "total_gpus": total_gpus,
            "avg_gpu_utilization": round(avg_gpu_util, 2),
        }
