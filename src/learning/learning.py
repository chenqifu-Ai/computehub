# ComputeHub Learning - Pattern Learning Store
# Inherited from OpenPC System gene/store pattern

import json
import os
import time
import logging
from typing import Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("computehub.learning")


@dataclass
class LearningPattern:
    name: str
    description: str
    context: dict
    success_rate: float
    usage_count: int
    created_at: float
    last_used: float


class LearningStore:
    """
    Persistent learning store - stores and recalls execution patterns.
    Inherited from OpenPC System gene/store pattern.
    """
    def __init__(self, store_path: str = "./genes.json"):
        self.store_path = store_path
        self._patterns: dict[str, LearningPattern] = {}
        self._load()
        logger.info(f"✅ LearningStore initialized: {len(self._patterns)} patterns loaded")
    
    def learn(self, context: dict, success: bool, duration: float) -> str:
        """Learn from an execution and store the pattern."""
        name = self._generate_pattern_name(context)
        
        if name in self._patterns:
            p = self._patterns[name]
            p.usage_count += 1
            p.last_used = time.time()
            p.success_rate = (p.success_rate * (p.usage_count - 1) + (1 if success else 0)) / p.usage_count
        else:
            self._patterns[name] = LearningPattern(
                name=name,
                description=f"Pattern for {context.get('framework', 'unknown')}",
                context=context,
                success_rate=1.0 if success else 0.0,
                usage_count=1,
                created_at=time.time(),
                last_used=time.time(),
            )
        
        self._save()
        logger.info(f"📚 Learned pattern: {name} (usage={self._patterns[name].usage_count}, success={self._patterns[name].success_rate:.1%})")
        return name
    
    def recall(self, context: dict, threshold: float = 0.8) -> Optional[LearningPattern]:
        """Recall a similar pattern from memory."""
        best = None
        best_score = 0.0
        
        for name, p in self._patterns.items():
            score = self._match_score(p.context, context)
            if score >= threshold and p.success_rate > best_score:
                best = p
                best_score = p.success_rate
        
        if best:
            logger.info(f"🔄 Pattern recalled: {best.name} (score={best_score:.2f})")
        return best
    
    def status(self) -> dict:
        return {
            "total_patterns": len(self._patterns),
            "patterns": [
                {
                    "name": p.name,
                    "usage_count": p.usage_count,
                    "success_rate": p.success_rate,
                }
                for p in self._patterns.values()
            ],
        }
    
    def _generate_pattern_name(self, context: dict) -> str:
        return f"{context.get('framework', 'unknown')}_{context.get('gpu_required', 0)}gpu"
    
    def _match_score(self, pattern_ctx: dict, query_ctx: dict) -> float:
        if pattern_ctx.get("framework") != query_ctx.get("framework"):
            return 0.0
        return 0.9  # Same framework match
    
    def _load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path) as f:
                    data = json.load(f)
                    for name, p in data.items():
                        self._patterns[name] = LearningPattern(**p)
            except:
                pass
    
    def _save(self):
        with open(self.store_path, 'w') as f:
            json.dump({k: asdict(v) for k, v in self._patterns.items()}, f, indent=2)
