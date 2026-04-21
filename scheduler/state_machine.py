from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-FSM")

class TaskStatus(Enum):
    PENDING = "PENDING"           # 任务提交，等待匹配
    MATCHING = "MATCHING"         # 调度器正在寻找最优物理节点
    DEPLOYING = "DEPLOYING"       # 任务正在分发至节点
    EXECUTING = "EXECUTING"       # 节点正在物理执行
    VERIFYING = "VERIFYING"       # 结果回传，等待物理验证/双节点比对
    COMPLETED = "COMPLETED"       # 验证通过，结算完成
    FAILED = "FAILED"             # 执行失败/节点崩溃
    CANCELLED = "CANCELLED"       # 用户取消

class TaskStateMachine:
    """
    ComputeHub 任务状态机：定义算力任务在全局网络中的确定性转移路径
    """
    # 定义合法状态转移矩阵
    TRANSITIONS = {
        TaskStatus.PENDING: [TaskStatus.MATCHING, TaskStatus.CANCELLED],
        TaskStatus.MATCHING: [TaskStatus.DEPLOYING, TaskStatus.FAILED, TaskStatus.CANCELLED],
        TaskStatus.DEPLOYING: [TaskStatus.EXECUTING, TaskStatus.FAILED],
        TaskStatus.EXECUTING: [TaskStatus.VERIFYING, TaskStatus.FAILED],
        TaskStatus.VERIFYING: [TaskStatus.COMPLETED, TaskStatus.FAILED],
        TaskStatus.FAILED: [TaskStatus.MATCHING], # 失败后可尝试重新匹配
        TaskStatus.COMPLETED: [], # 终态
        TaskStatus.CANCELLED: []  # 终态
    }

    @classmethod
    def validate_transition(cls, current: TaskStatus, next_status: TaskStatus) -> bool:
        """
        验证状态转移是否合法
        """
        if next_status in cls.TRANSITIONS.get(current, []):
            return True
        logger.error(f"Illegal state transition attempted: {current.value} -> {next_status.value}")
        return False

    @classmethod
    def transition(cls, current: TaskStatus, next_status: TaskStatus):
        """
        执行状态转移
        """
        if cls.validate_transition(current, next_status):
            logger.info(f"State Transition: {current.value} -> {next_status.value}")
            return next_status
        raise ValueError(f"Invalid transition from {current.value} to {next_status.value}")

# 简单测试
if __name__ == "__main__":
    try:
        state = TaskStatus.PENDING
        state = TaskStateMachine.transition(state, TaskStatus.MATCHING)
        state = TaskStateMachine.transition(state, TaskStatus.DEPLOYING)
        state = TaskStateMachine.transition(state, TaskStatus.EXECUTING)
        state = TaskStateMachine.transition(state, TaskStatus.VERIFYING)
        state = TaskStateMachine.transition(state, TaskStatus.COMPLETED)
        print("✅ Deterministic Path Validated: PENDING -> COMPLETED")
        
        # 测试非法转移
        TaskStateMachine.transition(TaskStatus.PENDING, TaskStatus.COMPLETED)
    except ValueError as e:
        print(f"✅ Caught expected illegal transition: {e}")
