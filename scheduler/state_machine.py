import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import time
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeHub-FSM")

class TaskState(Enum):
    """
    Soul-Engine: The Absolute State Machine
    Strictly defines the physical transition of a task across the distributed network.
    """
    SUBMITTED = "SUBMITTED"     # S0: Received by Gateway, waiting for match
    DISPATCHED = "DISPATCHED"   # S1: Matched to node, command sent to Node
    DEPLOYING = "DEPLOYING"     # S2: Node acknowledged, pulling environment/data
    EXECUTING = "EXECUTING"     # S3: Physical computation in progress
    VERIFYING = "VERIFYING"     # S4: Result received, undergoing redundancy check
    COMPLETED = "COMPLETED"     # S5: Verified and settled
    FAILED = "FAILED"           # Error state
    CANCELLED = "CANCELLED"     # User/System terminated

@dataclass
class TaskContext:
    task_id: str
    task_name: str
    requirements: dict
    current_state: TaskState = TaskState.SUBMITTED
    assigned_node: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    last_transition: float = field(default_factory=time.time)
    history: List[Dict[str, Any]] = field(default_factory=list)
    result_hash: Optional[str] = None

class TaskStateMachine:
    """
    Deterministic Transition Engine.
    Ensures tasks move through the network without 'fuzzy' states.
    """
    def __init__(self):
        self.active_tasks: Dict[str, TaskContext] = {}
        
        # Define legal transitions to prevent state skipping or illegal jumps
        self._legal_transitions = {
            TaskState.SUBMITTED: [TaskState.DISPATCHED, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.DISPATCHED: [TaskState.DEPLOYING, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.DEPLOYING: [TaskState.EXECUTING, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.EXECUTING: [TaskState.VERIFYING, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.VERIFYING: [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.COMPLETED: [], # Terminal state
            TaskState.FAILED: [],    # Terminal state
            TaskState.CANCELLED: []  # Terminal state
        }

    def create_task(self, task_name: str, requirements: dict) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        ctx = TaskContext(task_id=task_id, task_name=task_name, requirements=requirements)
        self.active_tasks[task_id] = ctx
        self._log_transition(ctx, None, TaskState.SUBMITTED, "Task initialized")
        return task_id

    def transition(self, task_id: str, to_state: TaskState, reason: str = "") -> bool:
        """
        Strictly enforce state transition.
        """
        ctx = self.active_tasks.get(task_id)
        if not ctx:
            logger.error(f"FSM Error: Task {task_id} not found")
            return False

        if to_state not in self._legal_transitions[ctx.current_state]:
            logger.error(f"FSM Illegal Transition: {ctx.current_state.name} -> {to_state.name} | Task: {task_id}")
            return False

        old_state = ctx.current_state
        ctx.current_state = to_state
        ctx.last_transition = time.time()
        self._log_transition(ctx, old_state, to_state, reason)
        
        logger.info(f"FSM Transition: {task_id} [{old_state.name}] -> [{to_state.name}] | {reason}")
        return True

    def _log_transition(self, ctx: TaskContext, from_state: Optional[TaskState], to_state: TaskState, reason: str):
        ctx.history.append({
            "from": from_state.name if from_state else "START",
            "to": to_state.name,
            "timestamp": time.time(),
            "reason": reason
        })

    def get_task_status(self, task_id: str) -> Optional[dict]:
        ctx = self.active_tasks.get(task_id)
        if not ctx: return None
        return {
            "task_id": ctx.task_id,
            "state": ctx.current_state.name,
            "node": ctx.assigned_node,
            "duration": time.time() - ctx.start_time,
            "history": ctx.history
        }

if __name__ == "__main__":
    # Testing the Soul-Engine FSM
    fsm = TaskStateMachine()
    tid = fsm.create_task("AI-Model-Training", {"gpu": "A100"})
    
    # Valid flow
    fsm.transition(tid, TaskState.DISPATCHED, "Matched to node-alpha")
    fsm.transition(tid, TaskState.DEPLOYING, "Node acknowledged")
    fsm.transition(tid, TaskState.EXECUTING, "Computation started")
    
    # Test Illegal Jump (S3 -> S5)
    print("\nTesting Illegal Jump (EXECUTING -> COMPLETED)...")
    if not fsm.transition(tid, TaskState.COMPLETED, "Skipping verification"):
        print("✅ FSM successfully blocked illegal state jump.")
    
    # Test Valid Completion
    fsm.transition(tid, TaskState.VERIFYING, "Result received, checking hash")
    fsm.transition(tid, TaskState.COMPLETED, "Hash verified, settled")
    
    print("\nFinal Task Status:")
    print(fsm.get_task_status(tid))
