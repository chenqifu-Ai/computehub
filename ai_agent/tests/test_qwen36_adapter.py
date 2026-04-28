#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen3.6-35b 适配层 v2.0.0 测试套件
使用 pytest 运行: pytest tests/ -v
"""
import pytest
import os
import sys
import json
import time
import requests
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent.config.qwen36_adapter import (
    Qwen36Adapter,
    Qwen36Config,
    ConfigurationError,
    AdapterTimeout,
    AdapterHTTPError,
    AdapterRateLimitError,
    AdapterError,
    AdapterResponseError,
    PerformanceStats,
    ask,
    ask_detailed,
    ask_code,
    get_stats,
    health_check,
    reset_adapter,
    _setup_logger,
    _load_dotenv,
    __version__,
    __author__,
    __license__,
)

# ============================================================
# 测试数据
# ============================================================

SAMPLE_SUCCESS_RESPONSE = {
    "choices": [{
        "message": {
            "content": "正确答案",
            "reasoning": "推理过程：这是一个简单问题，答案是正确答案。"
        },
        "finish_reason": "stop",
    }],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }
}

SAMPLE_THINKING_RESPONSE = {
    "choices": [{
        "message": {
            "content": None,  # vLLM 的非标准响应
            "reasoning": "Thinking Process:\n1. Analyze...\n2. Plan...\nFinal Output:** \"最终答案\""
        },
        "finish_reason": "stop",
    }],
    "usage": {
        "prompt_tokens": 20,
        "completion_tokens": 50,
        "total_tokens": 70,
    }
}

SAMPLE_CODE_RESPONSE = {
    "choices": [{
        "message": {
            "content": "Here's the code:\n```python\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n```\n",
            "reasoning": "Thinking...\n\nHere's the code:\n```python\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n```\n"
        },
        "finish_reason": "stop",
    }],
    "usage": {
        "prompt_tokens": 15,
        "completion_tokens": 40,
        "total_tokens": 55,
    }
}

# ============================================================
# 配置测试
# ============================================================

class TestConfig:
    """Qwen36Config 测试"""

    def test_default_config(self):
        config = Qwen36Config()
        assert config.timeout == 120
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.model == "qwen3.6-35b-common"

    def test_custom_config(self):
        config = Qwen36Config(
            api_key="test-key",
            timeout=60,
            max_tokens=2048,
            temperature=0.5
        )
        assert config.api_key == "test-key"
        assert config.timeout == 60
        assert config.max_tokens == 2048
        assert config.temperature == 0.5

    def test_missing_api_key_raises_error(self):
        # 确保 .env 文件不存在
        env_path = Path(__file__).parent.parent / ".env"
        env_exists = env_path.exists()
        if env_exists:
            env_path.unlink()
        try:
            # 清除所有 QWEN36 环境变量
            for k in list(os.environ.keys()):
                if k.startswith("QWEN36_"):
                    del os.environ[k]
            with pytest.raises(ConfigurationError):
                Qwen36Config.from_env()
        finally:
            if env_exists:
                env_path.write_text(".env")

    def test_from_env(self):
        with patch.dict(os.environ, {
            "QWEN36_API_KEY": "test-key-from-env",
            "QWEN36_TIMEOUT": "60",
            "QWEN36_MODEL": "test-model",
        }):
            config = Qwen36Config.from_env()
            assert config.api_key == "test-key-from-env"
            assert config.timeout == 60
            assert config.model == "test-model"


# ============================================================
# 异常测试
# ============================================================

class TestExceptions:
    """自定义异常测试"""

    def test_adapter_error_hierarchy(self):
        assert issubclass(ConfigurationError, AdapterError)
        assert issubclass(AdapterTimeout, AdapterError)
        assert issubclass(AdapterHTTPError, AdapterError)
        assert issubclass(AdapterRateLimitError, AdapterError)
        assert issubclass(AdapterResponseError, AdapterError)

    def test_adapter_http_error_status_code(self):
        error = AdapterHTTPError("Server error", 500)
        assert error.status_code == 500

    def test_adapter_rate_limit_error(self):
        error = AdapterRateLimitError("Too many requests")
        assert "too many" in str(error).lower() or "rate" in str(error).lower()


# ============================================================
# 性能统计测试
# ============================================================

class TestPerformanceStats:
    """PerformanceStats 测试"""

    def test_initial_stats(self):
        stats = PerformanceStats()
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.avg_latency_ms == 0.0
        assert stats.error_rate == 0.0

    def test_stats_calculation(self):
        stats = PerformanceStats(
            total_calls=10,
            successful_calls=8,
            failed_calls=2,
            total_tokens=1000,
            total_latency_ms=5000.0
        )
        assert stats.avg_latency_ms == 625.0
        assert stats.error_rate == 0.2

    def test_summary(self):
        stats = PerformanceStats(
            total_calls=10,
            successful_calls=8,
            failed_calls=2,
            total_tokens=1000,
            total_latency_ms=5000.0
        )
        summary = stats.summary()
        assert "10" in summary
        assert "8" in summary
        assert "2" in summary

    def test_p95_p99_calculation(self):
        stats = PerformanceStats()
        # 添加一些测试延迟数据
        for i in range(100):
            stats.record_latency(float(i * 10))
        
        assert stats.p95_latency_ms >= 900.0
        assert stats.p99_latency_ms >= 950.0
        assert stats.min_latency_ms == 0.0
        assert stats.max_latency_ms == 990.0

    def test_daily_summary(self):
        stats = PerformanceStats()
        summary = stats.daily_summary("2026-04-29")
        assert summary["date"] == "2026-04-29"
        assert summary["total_calls"] == 0


# ============================================================
# 输出清洗测试
# ============================================================

class TestOutputCleaning:
    """_clean_output 测试"""

    def setup_method(self):
        # 创建临时适配器实例（不需要真实 API）
        self.adapter = Qwen36Config(api_key="test")  # 只为测试 _clean_output

    def test_short_text_returns_directly(self):
        clean = Qwen36Config(api_key="test")
        from ai_agent.config.qwen36_adapter import Qwen36Adapter
        adapter = Qwen36Adapter.__new__(Qwen36Adapter)
        assert adapter._clean_output("hello") == "hello"

    def test_code_block_extraction(self):
        from ai_agent.config.qwen36_adapter import Qwen36Adapter
        adapter = Qwen36Adapter.__new__(Qwen36Adapter)
        raw = """Thinking process:
Here's my code:
```python
def hello():
    return "world"
```
More thinking..."""
        result = adapter._clean_output(raw)
        assert "def hello" in result

    def test_quotes_extraction(self):
        from ai_agent.config.qwen36_adapter import Qwen36Adapter
        adapter = Qwen36Adapter.__new__(Qwen36Adapter)
        raw = """This is a long thinking process that goes on and on for many lines.
Here is some analysis and reasoning about the problem at hand with lots of detail.
The answer is "42"
Final output section with more text to make this even longer."""
        result = adapter._clean_output(raw)
        assert result == "42"

    def test_final_output_extraction(self):
        from ai_agent.config.qwen36_adapter import Qwen36Adapter
        adapter = Qwen36Adapter.__new__(Qwen36Adapter)
        raw = """Here is a very long thinking process that takes a while to complete.
1. Analyze the problem carefully and break it down into smaller parts.
2. Plan the solution with detailed steps and reasoning for each part.
Final Output:** "最终答案"
End of thinking with more filler text to make this longer than needed."""
        result = adapter._clean_output(raw)
        assert result == "最终答案"

    def test_last_line_extraction(self):
        from ai_agent.config.qwen36_adapter import Qwen36Adapter
        adapter = Qwen36Adapter.__new__(Qwen36Adapter)
        raw = """Here is a very long thinking process that takes a while to complete.
1. Analyze the problem carefully and break it down into smaller parts.
2. Plan the solution with detailed steps and reasoning for each part.
The correct answer is 42."""
        result = adapter._clean_output(raw)
        assert result == "The correct answer is 42."


# ============================================================
# API 调用测试 (mock)
# ============================================================

class TestAPICalls:
    """API 调用测试（mock）"""

    def test_successful_content_response(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=SAMPLE_SUCCESS_RESPONSE),
                raise_for_status=MagicMock()
            )
            result = adapter.ask("测试问题")
            assert "正确答案" in result

    def test_null_content_reasoning_fallback(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=SAMPLE_THINKING_RESPONSE),
                raise_for_status=MagicMock()
            )
            result = adapter.ask("测试问题")
            # 应该 fallback 到 reasoning 并清理
            assert "最终答案" in result

    def test_code_extraction(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=SAMPLE_CODE_RESPONSE),
                raise_for_status=MagicMock()
            )
            result = adapter.ask_code("快速排序")
            assert "quicksort" in result

    def test_401_error(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=401,
                text="Unauthorized"
            )
            with pytest.raises(ConfigurationError):
                adapter.ask("测试")

    def test_404_error(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=404,
                text="Not Found"
            )
            with pytest.raises(ConfigurationError):
                adapter.ask("测试")

    def test_429_rate_limit(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=429,
                text="Too Many Requests"
            )
            with pytest.raises(AdapterRateLimitError):
                adapter.ask("测试")

    def test_timeout_error(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            with pytest.raises(AdapterTimeout):
                adapter.ask("测试")

    def test_connection_error(self):
        adapter = Qwen36Adapter(config=Qwen36Config(api_key="test-key"))
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()
            with pytest.raises(AdapterError):
                adapter.ask("测试")


# ============================================================
# 版本测试
# ============================================================

class TestVersion:
    """版本信息测试"""

    def test_version_exists(self):
        assert __version__ == "2.0.0"

    def test_author_exists(self):
        assert __author__ == "小智 AI"

    def test_license_exists(self):
        assert __license__ == "MIT"


# ============================================================
# 运行测试
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
