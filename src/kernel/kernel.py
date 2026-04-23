# ComputeHub Kernel - Deterministic Task Scheduler
# Inherited from OpenPC System deterministic scheduling pattern
# Key principle: Linear queue eliminates race conditions

import logging
import threading
import time
from typing import Optional
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("computehub.kernel")


class TaskPriority(Enum):
    HIGH = 0
    MEDIUM = 1
    LOW = 2


@dataclass
class TaskUnit:
    """A unit of work to be processed by the kernel."""
    id: str
    action: str
    payload: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: float = field(default_factory=time.time)
    response_queue: Optional[deque] = field(default_factory=deque, repr=False)


class KernelState:
    """Immutable snapshot of kernel state for rollback support."""
    
    def __init__(self, queue_depth: int, processed_count: int, latency: float):
        self.queue_depth = queue_depth
        self.processed_count = processed_count
        self.last_latency = latency
    
    def __repr__(self):
        return f"KernelState(queue={self.queue_depth}, processed={self.processed_count}, latency={self.last_latency:.3f}s)"


class DeterministicKernel:
    """
    Deterministic kernel - processes tasks in a single-threaded linear queue.
    
    Architecture pattern (from OpenPC System):
        Client -> Gateway -> PurePipeline -> Kernel(Linear Queue) -> Executor -> Result
    
    Key properties:
    1. Single-threaded processing = no race conditions
    2. State mirror for rollback
    3. Priority-ordered queue
    """
    
    def __init__(self, queue_size: int = 1000, max_state_history: int = 10000):
        self._lock = threading.Lock()
        self._queue: deque = deque(maxlen=queue_size)
        self._max_states = max_state_history
        self._state_history: list = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._processed_count = 0
        self._last_latency = 0.0
        
        # Metrics
        self._total_processed = 0
        self._total_failed = 0
        self._total_time = 0.0
        
        logger.info(f"✅ Kernel initialized: queue_size={queue_size}, max_states={max_state_history}")
    
    def start(self):
        """Start the kernel processing loop."""
        if self._running:
            logger.warning("Kernel already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True, name="kernel-processor")
        self._thread.start()
        logger.info("🚀 Kernel started (linear processing)")
    
    def stop(self):
        """Stop the kernel."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("⏹️  Kernel stopped")
    
    def submit(self, task: TaskUnit) -> TaskUnit:
        """Submit a task to the linear queue."""
        with self._lock:
            # Insert in priority order
            queue_list = list(self._queue)
            inserted = False
            for i, existing in enumerate(queue_list):
                if task.priority.value < existing.priority.value:
                    queue_list.insert(i, task)
                    inserted = True
                    break
            if not inserted:
                queue_list.append(task)
            self._queue = deque(queue_list, maxlen=self._queue.maxlen)
        
        logger.info(f"📥 Task submitted: {task.id} ({task.action}, priority={task.priority.name})")
        return task
    
    def _process_loop(self):
        """Single-threaded processing loop - eliminates race conditions."""
        while self._running:
            try:
                task = self._queue.popleft()
                
                # Snapshot state before processing
                self._snapshot_state()
                
                start = time.time()
                
                # Process based on action
                result = self._handle_action(task)
                
                latency = time.time() - start
                self._last_latency = latency
                self._processed_count += 1
                self._total_processed += 1
                self._total_time += latency
                
                # Send result back
                if task.response_queue:
                    task.response_queue.append({
                        "success": result.get("success", False),
                        "data": result.get("data"),
                        "error": result.get("error"),
                    })
                
                logger.info(f"✅ Task completed: {task.id} ({latency*1000:.1f}ms)")
                
            except IndexError:
                # Queue empty, wait a bit
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"❌ Task failed: {e}")
                self._total_failed += 1
    
    def _handle_action(self, task: TaskUnit) -> dict:
        """Handle different task actions."""
        action = task.action.upper()
        payload = task.payload
        
        if action == "SUBMIT":
            # Task scheduling logic
            node = self._select_node(payload)
            if node:
                return {"success": True, "data": {"assigned_node": node, "status": "SCHEDULED"}}
            return {"success": False, "error": "No available node"}
        
        elif action == "STATUS":
            return {"success": True, "data": self.get_status()}
        
        elif action == "HEARTBEAT":
            # Update node status
            return {"success": True, "data": "heartbeat received"}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def _select_node(self, payload: dict) -> Optional[str]:
        """
        Simple node selection - selects first available node.
        Future: implement geographic + load-based selection.
        """
        # This would query the database for available nodes
        # For now, return a placeholder
        return None
    
    def _snapshot_state(self):
        """Save current kernel state for potential rollback."""
        state = KernelState(
            queue_depth=len(self._queue),
            processed_count=self._processed_count,
            latency=self._last_latency,
        )
        self._state_history.append(state)
        if len(self._state_history) > self._max_states:
            self._state_history.pop(0)
    
    def get_status(self) -> dict:
        """Get current kernel status."""
        return {
            "status": "RUNNING" if self._running else "STOPPED",
            "queue_depth": len(self._queue),
            "processed_count": self._processed_count,
            "total_processed": self._total_processed,
            "total_failed": self._total_failed,
            "average_latency_ms": (self._total_time / self._total_processed * 1000) if self._total_processed > 0 else 0,
            "last_latency_ms": self._last_latency * 1000,
            "state_history_count": len(self._state_history),
        }
    
    @property
    def queue_depth(self) -> int:
        return len(self._queue)
    
    @property
    def state_history(self) -> list:
        return self._state_history
