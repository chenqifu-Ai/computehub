#!/usr/bin/env python3
"""
JSON Extractor for reasoning-first models
==========================================
专为 reasoning-first 大模型设计的 JSON 提取工具。

问题背景:
  reasoning-first 模型（如 qwen3.6-35b on vLLM）的 content 字段始终为 null，
  所有输出（包括推理过程和最终答案）都在 reasoning 字段中。
  即使用 system prompt 要求"只返回JSON"，模型也会在 reasoning 中先写一段思考。

解决方案:
  1. 从 reasoning 字段提取最后一个 JSON 块
  2. 支持多种格式: JSON object, JSON array, JSON 包裹在 markdown 中
  3. 自动清理推理过程中的干扰文本

使用示例:
    >>> from json_extractor import extract_json_from_reasoning
    >>> reasoning = 'Here\'s a thinking process... 最终答案: {"name":"张三","age":30}'
    >>> result = extract_json_from_reasoning(reasoning)
    >>> print(result)  # {'name': '张三', 'age': 30}
"""

import json
import re
from typing import Any, Optional


def extract_json_from_reasoning(reasoning: str) -> Optional[Any]:
    """
    从 reasoning-first 模型的 reasoning 字段中提取 JSON 数据。

    提取策略（按优先级）:
    1. 直接解析整个 reasoning（如果本身就是 JSON）
    2. 查找 markdown 代码块中的 JSON (```json ... ```)
    3. 查找 JSON 数组 [...]
    4. 查找最后一个 JSON 对象 {...}
    5. 查找第一个 JSON 对象 {...}

    Args:
        reasoning: reasoning-first 模型的 reasoning 字段内容

    Returns:
        解析后的 Python 对象，失败返回 None

    Examples:
        # 基本对象
        >>> extract_json_from_reasoning('{"name":"张三","age":30}')
        {'name': '张三', 'age': 30}

        # 数组
        >>> extract_json_from_reasoning('[{"id":1},{"id":2}]')
        [{'id': 1}, {'id': 2}]

        # 带推理过程
        >>> extract_json_from_reasoning('思考过程... 最终答案: {"status":"ok"}')
        {'status': 'ok'}

        # markdown 包裹
        >>> extract_json_from_reasoning('```json\n{"a":1}\n```')
        {'a': 1}
    """
    if not reasoning:
        return None

    # 策略1: 直接解析整个 reasoning
    try:
        return json.loads(reasoning.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    # 策略2: 提取 markdown 代码块中的 JSON
    markdown_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
    markdown_matches = re.findall(markdown_pattern, reasoning)
    if markdown_matches:
        for block in markdown_matches:
            block = block.strip()
            try:
                return json.loads(block)
            except (json.JSONDecodeError, ValueError):
                pass

    # 策略3: 提取 JSON 数组 [...]
    array_pattern = r'\[.*\]'
    array_match = re.search(array_pattern, reasoning, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group())
        except (json.JSONDecodeError, ValueError):
            pass

    # 策略4: 提取最后一个 JSON 对象 {...}（最可能是最终答案）
    # 支持嵌套对象
    json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
    json_blocks = re.findall(json_pattern, reasoning)
    if json_blocks:
        try:
            return json.loads(json_blocks[-1])
        except (json.JSONDecodeError, ValueError):
            pass

    # 策略5: 提取第一个 JSON 对象（保底方案）
    if json_blocks:
        try:
            return json.loads(json_blocks[0])
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def extract_json_from_response(response_data: dict) -> Optional[Any]:
    """
    从 OpenAI 兼容 API 的完整响应中提取 JSON。

    自动处理 reasoning-first 模型：
    - content 为 null → 从 reasoning 提取
    - reasoning-first → 优先取 reasoning 字段

    Args:
        response_data: OpenAI API 响应的 JSON 数据

    Returns:
        提取的 JSON 对象，失败返回 None

    Example:
        >>> resp = requests.post(url, json=payload).json()
        >>> data = extract_json_from_response(resp)
    """
    if not response_data or "choices" not in response_data:
        return None

    msg = response_data["choices"][0].get("message", {})

    # 优先从 reasoning 字段提取（reasoning-first 模型）
    reasoning = msg.get("reasoning") or ""
    if reasoning:
        return extract_json_from_reasoning(reasoning)

    # 其次从 content 提取（普通模型）
    content = msg.get("content") or ""
    if content:
        return extract_json_from_reasoning(content)

    return None


def extract_json_array_from_response(response_data: dict) -> Optional[list]:
    """
    从响应中提取 JSON 数组。

    专门处理返回 JSON 数组的场景。
    """
    result = extract_json_from_response(response_data)
    if isinstance(result, list):
        return result
    return None


def extract_json_object_from_response(response_data: dict) -> Optional[dict]:
    """
    从响应中提取 JSON 对象。

    专门处理返回 JSON 对象的场景。
    """
    result = extract_json_from_response(response_data)
    if isinstance(result, dict):
        return result
    return None


# 便捷函数
def parse_json(reasoning: str) -> Optional[Any]:
    """快捷函数：解析 reasoning 中的 JSON"""
    return extract_json_from_reasoning(reasoning)


def safe_json_response(response_data: dict, default: Any = None) -> Any:
    """
    安全解析 API 响应中的 JSON，失败返回默认值。

    Args:
        response_data: API 响应
        default: 解析失败时的默认值

    Returns:
        解析结果或 default
    """
    result = extract_json_from_response(response_data)
    return result if result is not None else default


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("JSON Extractor 测试")
    print("=" * 60)

    tests = [
        # (描述, reasoning 输入, 期望是否成功)
        ("基本对象", '{"name":"张三","age":30}', True),
        ("带推理过程", "思考过程... 最终答案: {\"status\":\"ok\"}", True),
        ("JSON 数组", '[{"id":1},{"id":2}]', True),
        ("markdown 包裹", "```json\n{\"a\":1}\n```", True),
        ("纯文本（无 JSON）", "这是一段普通文本，没有 JSON", False),
        ("空字符串", "", False),
        ("嵌套对象", '{"user":{"name":"李四","scores":[90,85,92]}}', True),
        ("布尔和数字", '{"active":true,"count":42,"pi":3.14}', True),
    ]

    passed = 0
    for desc, input_str, expect_success in tests:
        result = extract_json_from_reasoning(input_str)
        success = (result is not None) == expect_success
        status = "✅" if success else "❌"
        print(f"  {status} {desc:12} | 结果: {result}")
        if success:
            passed += 1

    print(f"\n测试结果: {passed}/{len(tests)} 通过")
    print("=" * 60)
