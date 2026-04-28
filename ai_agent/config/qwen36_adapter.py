#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen3.6-35b API 统一适配层 v2.0.0
====================================
版本历史:
  v2.0.0 (2026-04-29): 工程化改造 - 配置管理/错误处理/版本控制
  v1.0.0 (2026-04-24): 初始版本 - content字段优先策略

核心发现：
  这个模型的 reasoning 字段 = 全部输出
  模型的 "thinking" 输出包含大量元信息
  这些元信息不是真正的回答

解决方案：
  1. system prompt 中明确禁止输出推理过程
  2. 优先读取 content 字段，fallback 到 reasoning
  3. 提供多种调用模式
"""

__version__ = "2.0.0"
__author__ = "小智 AI"
__license__ = "MIT"

import re
import os
import sys
import json
import time
import logging
import datetime
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

# ============================================================
# 配置管理 (支持环境变量 + .env 文件)
# ============================================================
@dataclass
class Qwen36Config:
    """适配层配置"""
    api_url: str = "https://ai.zhangtuokeji.top:9090/v1/chat/completions"
    api_key: str = ""  # 必须从环境变量获取
    model: str = "qwen3.6-35b-common"
    timeout: int = 120
    max_tokens: int = 4096
    temperature: float = 0.7
    log_level: str = "INFO"
    token_log_dir: str = field(default=None, repr=False)

    def __post_init__(self):
        if not self.token_log_dir:
            self.token_log_dir = os.path.join(
                str(Path.home()), ".openclaw", "workspace",
                "ai_agent", "results"
            )

    @classmethod
    def from_env(cls) -> 'Qwen36Config':
        """从环境变量创建配置"""
        # 尝试加载 .env 文件
        _load_dotenv()

        # 读取环境变量，有默认值
        api_url = os.getenv("QWEN36_API_URL",
            "https://ai.zhangtuokeji.top:9090/v1/chat/completions")
        api_key = os.getenv("QWEN36_API_KEY", "")
        model = os.getenv("QWEN36_MODEL", "qwen3.6-35b-common")
        timeout = int(os.getenv("QWEN36_TIMEOUT", "120"))
        max_tokens = int(os.getenv("QWEN36_MAX_TOKENS", "4096"))
        temperature = float(os.getenv("QWEN36_TEMPERATURE", "0.7"))
        log_level = os.getenv("QWEN36_LOG_LEVEL", "INFO")

        # 验证必要配置
        if not api_key:
            raise ConfigurationError(
                "QWEN36_API_KEY 未配置！\n"
                "请设置环境变量或创建 .env 文件"
            )

        return cls(
            api_url=api_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
            log_level=log_level
        )


def _load_dotenv():
    """加载 .env 文件（无需 python-dotenv）"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and not os.getenv(key):
                    os.environ[key] = value


# ============================================================
# 自定义异常类
# ============================================================
class AdapterError(Exception):
    """适配层基类异常"""
    pass


class ConfigurationError(AdapterError):
    """配置错误"""
    pass


class AdapterTimeout(AdapterError):
    """API 请求超时"""
    pass


class AdapterHTTPError(AdapterError):
    """HTTP 错误"""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)


class AdapterRateLimitError(AdapterError):
    """速率限制"""
    pass


class AdapterResponseError(AdapterError):
    """响应格式错误"""
    pass


# ============================================================
# 日志配置
# ============================================================
def _setup_logger(level: str = "INFO") -> logging.Logger:
    """配置结构化日志"""
    logger = logging.getLogger("qwen36_adapter")
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台处理器
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(console)

    # 文件处理器（JSON 格式）
    try:
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "qwen36_adapter.log",
            encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(
            json.dumps({
                "timestamp": "%(asctime)s",
                "level": "%(levelname)s",
                "module": "%(name)s",
                "message": "%(message)s"
            }, ensure_ascii=False)
        ))
        logger.addHandler(file_handler)
    except Exception:
        pass  # 文件写入失败不影响功能

    return logger


# ============================================================
# Token 使用量记录
# ============================================================
_TOKEN_LOG_DIR = None
_TOKEN_LOG_FILE = None
_CONVERSATION_LOG_FILE = None

def _init_logs():
    global _TOKEN_LOG_DIR, _TOKEN_LOG_FILE, _CONVERSATION_LOG_FILE
    _TOKEN_LOG_DIR = os.path.join(
        str(Path.home()), ".openclaw", "workspace",
        "ai_agent", "results"
    )
    _TOKEN_LOG_FILE = os.path.join(_TOKEN_LOG_DIR, "token_usage.jsonl")
    _CONVERSATION_LOG_FILE = os.path.join(
        _TOKEN_LOG_DIR, "conversation_debug.jsonl"
    )
    os.makedirs(_TOKEN_LOG_DIR, exist_ok=True)


def _log_token_usage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model: str = "qwen3.6-35b-common",
):
    """记录 token 使用量到日志文件"""
    try:
        os.makedirs(_TOKEN_LOG_DIR, exist_ok=True)
        entry = {
            "time": datetime.datetime.now().isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
        with open(_TOKEN_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Token 记录失败: {e}")


def _log_conversation(request_data: dict, response_data: dict, error: str = None):
    """记录完整对话到日志"""
    global _call_count
    _call_count += 1
    os.makedirs(_TOKEN_LOG_DIR, exist_ok=True)

    log_entry = {
        "id": _call_count,
        "time": datetime.datetime.now().isoformat(),
        "request": request_data,
        "response": response_data if response_data else {},
        "error": error,
    }

    with open(_CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")


# ============================================================
# 性能监控
# ============================================================
@dataclass
class PerformanceStats:
    """性能统计"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    _latencies: list = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(1, self.successful_calls)

    @property
    def error_rate(self) -> float:
        total = self.successful_calls + self.failed_calls
        return self.failed_calls / max(1, total)

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        return (
            f"统计: 调用{self.total_calls}次 | 成功{self.successful_calls}次 | "
            f"失败{self.failed_calls}次 | 错误率{self.error_rate:.1%} | "
            f"平均延迟{self.avg_latency_ms:.0f}ms | Token总消耗{self.total_tokens}"
        )


# ============================================================
# 全局变量
# ============================================================
logger = _setup_logger()
_call_count = 0
_performance = PerformanceStats()


# ============================================================
# Qwen36Adapter
# ============================================================
class Qwen36Adapter:
    """qwen3.6-35b API 适配器 v2.0.0"""

    def __init__(self, config: Qwen36Config = None, **kwargs):
        if config is None:
            config = Qwen36Config(**kwargs)

        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        self._call_count = 0
        _init_logs()

        logger.info(f"适配层初始化 | 模型: {config.model} | URL: {config.api_url}")

    def _call(
        self,
        messages: List[Dict],
        max_tokens: int = None,
        temperature: float = None,
    ) -> Dict:
        """调用 API（核心方法）"""
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        request_data = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        _performance.total_calls += 1
        start_time = time.time()

        try:
            resp = requests.post(
                self.config.api_url,
                headers=self.headers,
                json=request_data,
                timeout=self.config.timeout
            )
            elapsed_ms = (time.time() - start_time) * 1000
            _performance.total_latency_ms += elapsed_ms

            # 错误状态码处理
            if resp.status_code == 429:
                _performance.failed_calls += 1
                raise AdapterRateLimitError(f"速率限制: {resp.text[:200]}")

            if resp.status_code >= 500:
                _performance.failed_calls += 1
                raise AdapterHTTPError(f"服务器错误 {resp.status_code}", resp.status_code)

            if resp.status_code == 401:
                _performance.failed_calls += 1
                raise ConfigurationError("API Key 无效或已过期")

            if resp.status_code == 404:
                _performance.failed_calls += 1
                raise ConfigurationError(f"模型 {self.config.model} 不存在")

            if resp.status_code == 400:
                _performance.failed_calls += 1
                raise ConfigurationError(f"请求错误: {resp.text[:200]}")

            resp.raise_for_status()
            data = resp.json()

            # 提取响应
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or ""

            # 核心逻辑：优先 content，fallback reasoning
            raw = content.strip() if content.strip() else reasoning.strip()

            # 提取 usage
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            _performance.total_tokens += total_tokens
            _performance.successful_calls += 1

            # 记录日志
            _log_token_usage(prompt_tokens, completion_tokens, total_tokens, self.config.model)
            _log_conversation(request_data, data)

            # 性能日志
            if elapsed_ms > 5000:
                logger.warning(f"慢请求: {elapsed_ms:.0f}ms > 5000ms")

            return {
                "raw": raw,
                "reasoning": reasoning,
                "content": content,
                "finish_reason": data["choices"][0].get("finish_reason"),
                "usage": usage,
                "latency_ms": elapsed_ms,
            }

        except requests.exceptions.Timeout:
            _performance.failed_calls += 1
            raise AdapterTimeout(f"API 请求超时 ({self.config.timeout}s)")
        except requests.exceptions.ConnectionError as e:
            _performance.failed_calls += 1
            raise AdapterError(f"网络连接失败: {e}")
        except AdapterError:
            raise
        except Exception as e:
            _performance.failed_calls += 1
            logger.error(f"未知错误: {e}")
            raise AdapterError(f"API 调用失败: {e}")

    def ask(
        self,
        prompt: str,
        system: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """
        简洁调用：直接返回答案。

        Args:
            prompt: 用户问题
            system: 可选的系统提示词
            max_tokens: 可选的最大 token 数
            temperature: 可选的温度参数

        Returns:
            简洁的回答文本
        """
        sys = (
            "你是一个简洁高效的助手。\n"
            "规则：\n"
            "1. 直接回答问题\n"
            "2. 不要输出 'Thinking Process' 或分析步骤\n"
            "3. 不要有 'Final Answer' 或 'Final Output' 等元信息\n"
            "4. 只输出最终答案\n"
            "5. 回答要简洁"
        )
        if system:
            sys = system + "\n" + sys

        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt},
        ]
        result = self._call(messages, max_tokens, temperature)
        return self._clean_output(result["raw"])

    def ask_reasoned(self, prompt: str, system: str = None) -> Dict[str, str]:
        """
        允许推理的调用：返回 { "answer": "...", "thinking": "..." }
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        result = self._call(messages)
        answer = self._extract_last_meaningful(result["raw"])
        thinking = self._extract_thinking(result["raw"], answer)
        return {"answer": answer, "thinking": thinking}

    def ask_code(
        self,
        prompt: str,
        language: str = "Python",
        max_tokens: int = None,
    ) -> str:
        """代码生成：引导输出代码块"""
        sys = (
            f"你是{language}专家。\n"
            "输出格式：\n"
            "```python\n"
            "代码（必须包含测试代码和print输出）\n"
            "```\n"
            "代码必须包含测试用例，在main中调用并print结果。\n"
            "不要输出推理过程。"
        )
        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt},
        ]
        result = self._call(messages, max_tokens)
        raw = result["raw"]

        # 提取代码块
        lang = language.lower()
        blocks = re.findall(r'```' + re.escape(lang) + r'\s*\n(.*?)```', raw, re.DOTALL)

        if not blocks:
            parts = re.split(r'`python\s*\n', raw)
            for part in parts[1:]:
                close = part.find('``')
                if close > 0:
                    code = part[:close]
                else:
                    close2 = part.find('```')
                    if close2 > 0:
                        code = part[:close2]
                    else:
                        code = part
                blocks.append(code.strip())

        if not blocks:
            blocks = re.findall(r'```\w*\s*\n(.*?)```', raw, re.DOTALL)

        if not blocks:
            blocks = re.findall(r'`(.*?)`', raw, re.DOTALL)
            blocks = [b for b in blocks if 'class ' in b or 'def ' in b]

        if blocks:
            best = max(blocks, key=len)
            return best.strip()

        return self._clean_output(raw)

    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self.ask("你好")
            return len(result) > 0
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

    def get_stats(self) -> dict:
        """获取性能统计"""
        return _performance.to_dict()

    def get_stats_summary(self) -> str:
        """获取性能统计摘要"""
        return _performance.summary()

    # ============================================================
    # 输出清洗（内部方法）
    # ============================================================

    def _clean_output(self, raw: str) -> str:
        """
        清理模型输出，去掉推理元信息。

        提取优先级：
        1. 代码块（```...```）- 这些是实际答案
        2. 引号内容（"..."）
        3. Final Output 后面的内容
        4. 最后一行非空文字
        """
        text = raw.strip()

        if len(text) <= 100:
            return text

        # 1. 提取代码块
        code_blocks = re.findall(r'```(?:\w*)\s*\n(.*?)```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[-1].strip()

        # 2. 找引号包裹的内容
        quotes = re.findall(r'"([^"]+)"', text)
        if quotes:
            last_quote = quotes[-1]
            if len(last_quote) <= 500:
                return last_quote

        # 3. 找 Final Output 后面的内容
        m = re.search(r'Final Output[^"]*["\']([^"\']+)["\']', text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # 4. 取最后一行非空文字
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            skip_keywords = [
                "thinking process", "here's a thinking",
                "here is a thinking", "final output", "final answer",
                "let me", "好的，", "check:", "verify:", "confirmation:",
            ]
            clean_lines = [
                l for l in lines
                if not any(kw in l.lower() for kw in skip_keywords)
            ]
            if clean_lines:
                return clean_lines[-1]

        return text

    def _extract_last_meaningful(self, raw: str) -> str:
        """提取最后一段有意义的文字作为 answer"""
        text = raw.strip()
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        skip_patterns = [
            "thinking process", "here's a thinking", "let me",
            "好的，", "analysis of", "determine the",
        ]

        for para in reversed(paragraphs):
            if not any(p in para.lower() for p in skip_patterns):
                return para

        return paragraphs[-1] if paragraphs else text

    def _extract_thinking(self, raw: str, answer: str) -> str:
        """从 raw 中提取推理过程（去掉答案部分）"""
        text = raw.strip()
        idx = text.find(answer.strip())
        if idx > 0:
            return text[:idx].strip()
        return ""


# ============================================================
# 全局单例
# ============================================================
_adapter = None


def get_adapter() -> Qwen36Adapter:
    """获取全局适配层实例（单例模式）"""
    global _adapter
    if _adapter is None:
        _adapter = Qwen36Adapter()
    return _adapter


def reset_adapter():
    """重置全局适配器（用于测试）"""
    global _adapter
    _adapter = None


# ============================================================
# 便捷函数
# ============================================================
def ask(prompt: str, system: str = None, **kwargs) -> str:
    """便捷调用：简洁回答"""
    return get_adapter().ask(prompt, system, **kwargs)


def ask_detailed(prompt: str, system: str = None) -> Dict[str, str]:
    """便捷调用：带推理的回答"""
    return get_adapter().ask_reasoned(prompt, system)


def ask_code(prompt: str, language: str = "Python") -> str:
    """便捷调用：代码生成"""
    return get_adapter().ask_code(prompt, language)


def get_stats() -> dict:
    """获取性能统计"""
    return get_adapter().get_stats()


def health_check() -> bool:
    """健康检查"""
    return get_adapter().health_check()


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"🧪 qwen3.6-35b 适配层 v{__version__} 测试")
    print("=" * 60)

    try:
        adapter = Qwen36Adapter.from_env()
    except ConfigurationError as e:
        print(f"❌ 配置错误: {e}")
        print("请设置 QWEN36_API_KEY 环境变量或创建 .env 文件")
        sys.exit(1)

    print(f"\n📡 配置: 模型={adapter.config.model} | "
          f"URL={adapter.config.api_url} | "
          f"超时={adapter.config.timeout}s")

    print("\n1. 健康检查:")
    ok = adapter.health_check()
    print(f"   {'✅ 正常' if ok else '❌ 异常'}")

    print("\n2. 简单问题:")
    try:
        r = adapter.ask("1+1等于多少？")
        print(f"   回答: {r}")
        print(f"   长度: {len(r)} | {'✅ 简洁' if len(r) < 100 else '⚠️ 偏长'}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n3. 数学推理:")
    try:
        r = adapter.ask_reasoned("1/2 + 1/3 = ?")
        print(f"   回答: {r['answer'][:150]}")
        print(f"   推理: {len(r['thinking'])} 字符")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n4. 代码生成:")
    try:
        r = adapter.ask_code("快速排序")
        print(f"   代码: {r[:200]}")
        print(f"   长度: {len(r)}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n5. 性能统计:")
    print(f"   {adapter.get_stats_summary()}")

    print("\n✅ 测试完成")
