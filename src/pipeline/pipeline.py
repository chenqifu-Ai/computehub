"""任务净化管道 - 简化为2 Stage：Syntax + Security"""
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.core.logging import logger

FORBIDDEN_PATTERNS = ["rm -rf /", "rm -rf /*", ":(){ :|:& };:", "> /dev/sda", "mkfs.", "dd if="]


@dataclass
class FilterResult:
    passed: bool
    reason: str = ""
    cleaned: Any = None


class SyntaxFilter:
    """Stage 1: 基本格式校验"""

    def filter(self, input_data: Any) -> FilterResult:
        if not isinstance(input_data, dict):
            return FilterResult(False, "input must be a dict")
        if not input_data:
            return FilterResult(False, "empty input")
        if len(str(input_data)) > 100000:
            return FilterResult(False, "task too large")
        return FilterResult(True, cleaned=input_data)

    @property
    def name(self) -> str:
        return self.__class__.__name__


class SecurityFilter:
    """Stage 2: 安全检查"""

    def filter(self, input_data: dict) -> FilterResult:
        combined = f"{input_data.get('code_url', '')} {input_data.get('data_url', '')}"
        for pat in FORBIDDEN_PATTERNS:
            if pat in combined:
                return FilterResult(False, f"security violation: {pat}")
        return FilterResult(True, cleaned=input_data)

    @property
    def name(self) -> str:
        return self.__class__.__name__


class TaskPipeline:
    """任务净化管道 - Syntax → Security"""

    def __init__(self):
        self._filters = [
            SyntaxFilter(),
            SecurityFilter(),
        ]
        self._last_latency = 0.0
        self._blocked_count = 0
        logger.info(f"✅ TaskPipeline initialized with {len(self._filters)} filters")

    def process(self, task_data: dict) -> tuple[bool, dict, str]:
        """处理任务：通过返回 (True, cleaned_data, '')，拦截返回 (False, {}, reason)"""
        start = time.time()
        current = task_data

        for i, f in enumerate(self._filters, 1):
            result = f.filter(current)
            if not result.passed:
                self._blocked_count += 1
                reason = f"Stage {i} ({f.name}): {result.reason}"
                logger.warning(f"❌ {reason}")
                self._last_latency = time.time() - start
                return False, {}, reason
            current = result.cleaned

        self._last_latency = time.time() - start
        logger.info(f"✅ Pipeline passed ({self._last_latency*1000:.1f}ms)")
        return True, current, ""

    @property
    def status(self) -> dict:
        return {
            "status": "ACTIVE",
            "filters": len(self._filters),
            "blocked_count": self._blocked_count,
            "last_latency_ms": self._last_latency * 1000,
        }
