#!/usr/bin/env python3
"""
Model API Client - 统一模型调用封装
=====================================
专为 reasoning-first 模型设计的调用封装。

特性:
- 自动处理 reasoning-first 模型（content=null, 输出在 reasoning）
- 自动从 reasoning 中提取 JSON
- 自动处理流式输出中的控制字符
- 统一返回格式

使用示例:
    >>> from model_client import ModelClient
    >>> client = ModelClient()
    >>> # 纯文本
    >>> resp = client.chat("你是谁？")
    >>> print(resp.text)
    >>> # 要 JSON
    >>> resp = client.chat("返回JSON: {\"a\":1}", as_json=True)
    >>> print(resp.json_data)  # {'a': 1}
    >>> # 指定端点
    >>> resp = client.chat("你好", endpoint="vllm")  # 172.29.174.77:8765
"""

import requests
import json
import re
import time
from typing import Any, Optional
from enum import Enum

# 端点配置
ENDPOINTS = {
    "vllm": {  # vLLM 本地推理（最快，reasoning-first）
        "url": "http://172.29.174.77:8765/v1",
        "key": "sk-78sadn09bjawde123e",
        "reasoning": True,
    },
    "qwen8001": {  # qwen3.6-35b（推理-first）
        "url": "http://58.23.129.98:8001/v1",
        "key": "sk-78sadn09bjawde123e",
        "reasoning": True,
    },
    "gemma8000": {  # gemma-4-31b
        "url": "http://58.23.129.98:8000/v1",
        "key": "sk-vmkohy18-34ga;sjd",
        "reasoning": False,
    },
    "aliyun": {  # 阿里云百炼
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "key": "sk-65ca99f6fd55437fba47dc7ba7973242",
        "reasoning": False,
    },
    "zhangtuo": {  # 张拓科技
        "url": "https://ai.zhangtuokeji.top:9090/v1",
        "key": "sk-eVmVrxyJYmKAv7YzvJnauPBCl457mqvbSzUENMo70lBRIxH3",
        "reasoning": False,
    },
}


def extract_json(reasoning: str) -> Optional[Any]:
    """从 reasoning 字段提取 JSON（5级降级策略）"""
    if not reasoning:
        return None
    try:
        return json.loads(reasoning.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    # markdown 代码块
    for block in re.findall(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', reasoning):
        try:
            return json.loads(block.strip())
        except (json.JSONDecodeError, ValueError):
            pass
    # JSON 数组
    m = re.search(r'\[.*\]', reasoning, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except (json.JSONDecodeError, ValueError):
            pass
    # 最后一个 JSON 对象
    blocks = re.findall(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', reasoning)
    if blocks:
        try:
            return json.loads(blocks[-1])
        except (json.JSONDecodeError, ValueError):
            pass
    if blocks:
        try:
            return json.loads(blocks[0])
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def clean_json_text(text: str) -> str:
    """清理 JSON 文本中的控制字符"""
    if not text:
        return text
    # 移除非打印控制字符（保留换行和制表符）
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)


class ChatResponse:
    """统一聊天响应"""
    def __init__(self, data: dict, raw: dict, endpoint: str, elapsed: float):
        self.data = data
        self.raw = raw
        self.endpoint = endpoint
        self.elapsed = elapsed
        self.msg = data["choices"][0]["message"] if data.get("choices") else {}
        self._text = None
        self._json_data = None

    @property
    def text(self) -> str:
        """获取纯文本（自动处理 reasoning-first）"""
        if self._text is not None:
            return self._text
        # 优先 reasoning-first
        reasoning = self.msg.get("reasoning") or ""
        if reasoning:
            self._text = clean_json_text(reasoning)
        else:
            self._text = clean_json_text(self.msg.get("content") or "")
        return self._text

    @property
    def json_data(self) -> Optional[Any]:
        """获取 JSON 数据（自动从 reasoning 提取）"""
        if self._json_data is not None:
            return self._json_data
        self._json_data = extract_json(self.text)
        return self._json_data

    @property
    def usage(self) -> dict:
        return self.data.get("usage", {})

    def __str__(self):
        return self.text[:500] if self.text else "(empty)"


class ModelClient:
    """统一模型调用客户端"""

    def __init__(self, endpoint: str = "vllm"):
        if endpoint not in ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint}. Available: {list(ENDPOINTS.keys())}")
        self.endpoint = endpoint
        self.config = ENDPOINTS[endpoint]

    def chat(
        self,
        prompt: str,
        system: str = None,
        model: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        as_json: bool = False,
        timeout: int = 60,
        messages: list = None,
    ) -> ChatResponse:
        """
        发送聊天请求。

        Args:
            prompt: 用户消息
            system: system prompt（可选）
            model: 指定模型（默认使用 endpoint 的第一个模型）
            max_tokens: 最大 token 数
            temperature: 温度
            as_json: 是否只返回 JSON（自动从 reasoning 提取）
            timeout: 超时秒数
            messages: 完整消息历史（可选，覆盖 prompt/system）

        Returns:
            ChatResponse 对象，包含 .text, .json_data, .usage
        """
        # 构建消息
        if messages:
            msgs = list(messages)
        else:
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})

        payload = {
            "model": model or "qwen3.6-35b",
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start = time.time()
        r = requests.post(
            f"{self.config['url']}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.config['key']}"},
            json=payload,
            timeout=timeout,
        )
        elapsed = time.time() - start

        data = r.json()
        return ChatResponse(data, data, self.endpoint, elapsed)

    def chat_with_history(
        self,
        history: list,
        new_prompt: str,
        model: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """带完整历史的多轮对话"""
        messages = list(history)
        messages.append({"role": "user", "content": new_prompt})
        return self.chat(
            prompt="",
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )


# 便捷全局函数（适合快速调用）
_client_cache = {}

def chat(prompt: str, endpoint: str = "vllm", as_json: bool = False, **kwargs) -> ChatResponse:
    """快捷函数：直接调用模型"""
    if endpoint not in _client_cache:
        _client_cache[endpoint] = ModelClient(endpoint)
    resp = _client_cache[endpoint].chat(prompt, **kwargs)
    if as_json:
        print(f"📦 JSON: {json.dumps(resp.json_data, ensure_ascii=False, default=str)}")
        return resp
    print(f"⏱️  {resp.elapsed:.2f}s | 🔌 {endpoint}")
    print(resp.text[:500])
    return resp
