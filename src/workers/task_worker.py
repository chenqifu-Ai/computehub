# ComputeHub Workers - Background Task Worker

import time
import logging
import threading
from typing import Optional
from src.executor.executor import Executor, ExecutionResult
from src.learning.learning import LearningStore
from src.kernel.kernel import TaskUnit

logger = logging.getLogger("computehub.worker")


class TaskWorker:
    def __init__(self, executor: Executor, learning_store: LearningStore, max_concurrent: int = 4):
        self.executor = executor
        self.learning_store = learning_store
        self.max_concurrent = max_concurrent
        self._running = False
        self._task_counter = 0

    def start(self):
        self._running = True
        logger.info("🚀 TaskWorker started")

    def stop(self):
        self._running = False
        logger.info("⏹️ TaskWorker stopped")

    def process_task(self, task: TaskUnit) -> ExecutionResult:
        self._task_counter += 1
        logger.info(f"🔄 Processing task {task.id}: {task.action}")
        result = self.executor.execute(task.payload)
        self.learning_store.learn(
            context={"framework": task.payload.get("framework", "python"), "gpu_required": task.payload.get("gpu_required", 1)},
            success=result.status.value == "COMPLETED",
            duration=result.duration,
        )
        logger.info(f"✅ Task {task.id} done")
        return result

    def status(self) -> dict:
        return {"running": self._running, "tasks_processed": self._task_counter}
