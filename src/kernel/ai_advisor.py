"""AI 调度顾问 - 基于 DeepSeek 的智能调度建议

设计原则：
1. AI 是增强，不是依赖 — 失败时优雅降级到 round_robin
2. 后台异步调用 — 不阻塞请求响应
3. 数据驱动 — 基于历史执行数据做建议
4. 可观测 — 记录每次 AI 决策和实际结果
"""
import json
import os
import time
from typing import Optional

from src.core.logging import logger

# Ollama Cloud API 配置
OLLAMA_API_URL = "https://api.ollama.com/api/chat"
OLLAMA_API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
AI_MODEL = "deepseek-v4-flash"

# HTTP session with retries
import urllib.request
import urllib.error


def _call_deepseek(messages: list[dict], timeout: int = 30) -> Optional[dict]:
    """调用 DeepSeek-V4-Flash，返回解析后的 JSON"""
    payload = json.dumps({
        "model": AI_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3},  # 低温度，更确定性
    }).encode()

    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "ComputeHub/2.0-ai-scheduling",
        },
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
        msg = data.get("message", {})
        content = msg.get("content") or msg.get("thinking", "")
        return {"content": content, "raw": data}
    except Exception as e:
        logger.warning(f"⚠️  DeepSeek API call failed: {e}")
        return None


class AISchedulerAdvisor:
    """AI 调度顾问"""

    VALID_STRATEGIES = ("least_connections", "round_robin")

    def __init__(self, fallback_strategy: str = "round_robin"):
        self.fallback_strategy = fallback_strategy
        self._total_ai_calls = 0
        self._total_fallbacks = 0

    def get_recommendation(self, task_context: dict) -> dict:
        """获取 AI 调度建议

        Args:
            task_context: 任务上下文，包含 action, framework, gpu_required 等

        Returns:
            {
                "strategy": "least_connections" | "round_robin",
                "confidence": float,  # 0.0-1.0
                "reasoning": str,
                "ai_used": bool,  # 是否成功调用了 AI
            }
        """
        self._total_ai_calls += 1

        # 构建历史数据摘要（实际应用中从数据库查询）
        history_summary = self._get_history_summary(task_context)

        # 调用 DeepSeek
        messages = [
            {
                "role": "system",
                "content": """你是一个AI调度专家，负责为分布式计算任务选择最优调度策略。

可选策略：
1. least_connections: 选择当前活跃任务最少的节点（适合短任务、I/O密集型）
2. round_robin: 轮询分配（适合任务负载均衡、长任务）

基于任务特征和历史数据，选择最优策略。只返回JSON格式：
{"strategy": "least_connections", "confidence": 0.8, "reasoning": "简要说明"}
""",
            },
            {
                "role": "user",
                "content": f"""任务特征：
- action: {task_context.get('action', 'unknown')}
- framework: {task_context.get('framework', 'python')}
- gpu_required: {task_context.get('gpu_required', 1)}
- memory_required_gb: {task_context.get('memory_required_gb', 0)}

历史数据（相似任务）：
{json.dumps(history_summary, indent=2, ensure_ascii=False)}

请选择调度策略，只输出JSON。""",
            },
        ]

        result = _call_deepseek(messages)

        if result is None:
            self._total_fallbacks += 1
            logger.info("🤖 AI unavailable, using fallback strategy")
            return {
                "strategy": self.fallback_strategy,
                "confidence": 0.0,
                "reasoning": "AI unavailable, fallback to round_robin",
                "ai_used": False,
            }

        # 解析 AI 输出
        try:
            content = result["content"]
            # 提取 JSON
            import re
            json_match = re.search(r"\{[^}]+\}", content)
            if json_match:
                ai_decision = json.loads(json_match.group())
            else:
                ai_decision = json.loads(content)

            strategy = ai_decision.get("strategy", self.fallback_strategy)
            confidence = ai_decision.get("confidence", 0.5)
            reasoning = ai_decision.get("reasoning", "")

            # 校验策略是否合法
            if strategy not in self.VALID_STRATEGIES:
                strategy = self.fallback_strategy
                confidence = 0.0

            logger.info(f"🤖 AI recommends: {strategy} (confidence={confidence:.2f})")
            return {
                "strategy": strategy,
                "confidence": confidence,
                "reasoning": reasoning,
                "ai_used": True,
            }

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self._total_fallbacks += 1
            logger.warning(f"⚠️  AI response parse failed: {e}")
            return {
                "strategy": self.fallback_strategy,
                "confidence": 0.0,
                "reasoning": f"AI response parse failed, fallback: {e}",
                "ai_used": True,
            }

    def _get_history_summary(self, task_context: dict) -> dict:
        """获取历史数据摘要（后续从数据库查询）"""
        # TODO: 实际从 task_execution_history 表查询
        return {
            "total_similar_tasks": 0,
            "status": "no_historical_data",
            "note": "等待积累执行数据后再启用 AI 历史分析",
        }

    @property
    def stats(self) -> dict:
        return {
            "total_ai_calls": self._total_ai_calls,
            "total_fallbacks": self._total_fallbacks,
            "model": AI_MODEL,
        }
