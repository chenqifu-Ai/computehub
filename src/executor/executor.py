"""任务执行器 - 子进程执行"""
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum

from src.core.logging import logger


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ExecutionResult:
    status: TaskStatus
    output: str = ""
    error: str = ""
    duration: float = 0.0
    exit_code: int = 0


class Executor:
    """执行器 - Execute → Verify → Learn"""

    def __init__(self, sandbox_path: str = "/tmp/computehub"):
        self.sandbox_path = sandbox_path
        os.makedirs(sandbox_path, exist_ok=True)
        self._total_executed = 0
        self._total_failed = 0
        self._total_success = 0
        logger.info(f"✅ Executor initialized: sandbox={sandbox_path}")

    def execute(self, task: dict, timeout: int = 300) -> ExecutionResult:
        code_url = task.get("code_url", "")
        params = task.get("parameters", "")
        framework = task.get("framework", "python")
        task_id = task.get("id", "unknown")

        work_dir = os.path.join(self.sandbox_path, task_id)
        os.makedirs(work_dir, exist_ok=True)

        # Git clone if needed
        if code_url and code_url.startswith("http"):
            result = subprocess.run(
                ["git", "clone", "--depth=1", code_url, work_dir],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return ExecutionResult(status=TaskStatus.FAILED, error=f"Git clone failed: {result.stderr}")

        # Build command
        if framework == "python":
            cmd = ["python", "-c", params or "print('hello')"]
        elif framework == "shell":
            cmd = ["bash", "-c", params or "echo hello"]
        else:
            cmd = [framework, params] if params else [framework]

        try:
            start = time.time()
            result = subprocess.run(
                cmd, cwd=work_dir, capture_output=True, text=True, timeout=timeout,
            )
            duration = time.time() - start

            status = TaskStatus.COMPLETED if result.returncode == 0 else TaskStatus.FAILED
            exec_result = ExecutionResult(
                status=status,
                output=result.stdout,
                error=result.stderr,
                duration=duration,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            exec_result = ExecutionResult(
                status=TaskStatus.FAILED,
                error=f"Timeout after {timeout}s",
                duration=duration,
                exit_code=-1,
            )

        self._total_executed += 1
        if exec_result.status == TaskStatus.COMPLETED:
            self._total_success += 1
        else:
            self._total_failed += 1

        logger.info(f"📊 Execution: {task_id} | status={exec_result.status.value} | duration={duration:.2f}s")
        return exec_result

    @property
    def status(self) -> dict:
        rate = (self._total_success / self._total_executed * 100) if self._total_executed > 0 else 0
        return {
            "total_executed": self._total_executed,
            "total_success": self._total_success,
            "total_failed": self._total_failed,
            "success_rate": round(rate, 1),
        }
