# ComputeHub Pipeline - Multi-stage Task Purification
# Inherited from OpenPC System pure/pipeline pattern

import time
import logging
from typing import Any
from dataclasses import dataclass

logger = logging.getLogger("computehub.pipeline")


@dataclass
class FilterResult:
    passed: bool
    reason: str = ""
    cleaned: Any = None


class PureFilter:
    """Base filter interface."""
    def filter(self, input_data: Any) -> FilterResult:
        raise NotImplementedError
    def name(self) -> str:
        return type(self).__name__


class SyntaxFilter(PureFilter):
    """Stage 1: Basic format validation."""
    def filter(self, input_data: Any) -> FilterResult:
        if not isinstance(input_data, dict):
            return FilterResult(False, "input must be a dict")
        if not input_data:
            return FilterResult(False, "empty input")
        if len(str(input_data)) > 10000:
            return FilterResult(False, "task too large")
        return FilterResult(True, cleaned=input_data)


class SecurityFilter(PureFilter):
    """Stage 2: Security validation."""
    def __init__(self):
        self.forbidden = ["/etc/passwd", "/etc/shadow", "/root/.ssh", "rm -rf /"]
    
    def filter(self, input_data: Any) -> FilterResult:
        combined = f"{input_data.get('code_url','')} {input_data.get('data_url','')} {input_data.get('parameters','')}"
        for pat in self.forbidden:
            if pat in combined:
                return FilterResult(False, f"security violation: {pat}")
        return FilterResult(True, cleaned=input_data)


class ResourceFilter(PureFilter):
    """Stage 3: Resource feasibility check."""
    def filter(self, input_data: Any) -> FilterResult:
        gpu = input_data.get("gpu_required", 0)
        mem = input_data.get("memory_required_gb", 0)
        dur = input_data.get("duration_hours", 0)
        if gpu < 0 or gpu > 128:
            return FilterResult(False, f"invalid gpu count: {gpu}")
        if mem < 0 or mem > 4096:
            return FilterResult(False, f"invalid memory: {mem}GB")
        if dur < 0 or dur > 720:
            return FilterResult(False, f"invalid duration: {dur}h")
        return FilterResult(True, cleaned=input_data)


class ContextFilter(PureFilter):
    """Stage 4: Context enrichment."""
    def filter(self, input_data: Any) -> FilterResult:
        enriched = input_data.copy()
        enriched["pipeline_version"] = "2.0"
        enriched["validated_at"] = time.time()
        enriched["stages_passed"] = 4
        return FilterResult(True, cleaned=enriched)


class TaskPipeline:
    """
    Multi-stage task purification pipeline.
    Flow: Syntax -> Security -> Resource -> Context -> Ready
    """
    def __init__(self):
        self._filters = [
            SyntaxFilter(), SecurityFilter(),
            ResourceFilter(), ContextFilter(),
        ]
        self._last_latency = 0.0
        self._blocked_count = 0
        logger.info("✅ TaskPipeline initialized with 4 filters")
    
    def process(self, task_data: dict):
        start = time.time()
        current = task_data
        
        for i, f in enumerate(self._filters, 1):
            result = f.filter(current)
            if not result.passed:
                self._blocked_count += 1
                self._last_latency = time.time() - start
                logger.warning(f"❌ Stage {i} ({f.name()}) blocked: {result.reason}")
                return False, {}, f"Stage {i} ({f.name()}): {result.reason}"
            current = result.cleaned
        
        self._last_latency = time.time() - start
        logger.info(f"✅ Pipeline passed: {(self._last_latency*1000):.1f}ms")
        return True, current, ""
    
    def status(self) -> dict:
        return {
            "status": "ACTIVE",
            "filters": len(self._filters),
            "blocked_count": self._blocked_count,
            "last_latency_ms": self._last_latency * 1000,
        }
