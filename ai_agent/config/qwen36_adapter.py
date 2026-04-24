#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen3.6-35b API 统一适配层 v5 (最终版)
=======================================
核心发现：
  这个模型的 reasoning 字段 = 全部输出
  模型的 "thinking" 输出包含大量元信息（"Final Output Generation"等）
  这些元信息不是真正的回答，而是模型在"计划"要输出的内容

解决方案：
  1. system prompt 中明确禁止输出推理过程
  2. 直接读取 reasoning 字段作为 answer
  3. 提供多种调用模式
"""

import re
import os
import requests
from typing import Optional, Dict, Any, List


class Qwen36Adapter:
    """qwen3.6-35b API 适配器"""

    def __init__(self,
                 api_url: str = os.getenv("QWEN36_URL", "http://58.23.129.98:8000/v1/chat/completions"),
                 api_key: str = os.getenv("QWEN36_KEY", "sk-78sadn09bjawde123e"),
                 model: str = "qwen3.6-35b",
                 timeout: int = 120):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _call(self, messages: List[Dict], max_tokens=2000, temperature=0.7) -> Dict:
        """调用 API"""
        resp = requests.post(
            self.api_url, headers=self.headers,
            json={"model": self.model, "messages": messages,
                  "max_tokens": max_tokens, "temperature": temperature},
            timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        # 核心修复：content 字段才是正确答案，reasoning 只是推理过程
        # 旧逻辑：reasoning or content → 永远取 reasoning（因为总不为空）
        # 新逻辑：优先 content（干净答案），fallback reasoning
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        raw = content.strip() if content.strip() else reasoning.strip()
        return {
            "raw": raw,
            "reasoning": reasoning,
            "content": content,
            "finish_reason": data["choices"][0].get("finish_reason"),
            "usage": data.get("usage"),
        }

    def ask(self, prompt: str, system: str = None) -> str:
        """
        简洁调用：直接返回答案。
        
        关键：通过 system prompt 让模型不输出推理过程，
        这样 reasoning 字段 ≈ 直接回答。
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
        result = self._call(messages)
        
        # 提取有效内容：去掉模型输出的推理标记
        return self._clean_output(result["raw"])

    def ask_reasoned(self, prompt: str, system: str = None) -> Dict:
        """
        允许推理的调用：返回 { "answer": "...", "thinking": "..." }
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        result = self._call(messages)
        # 取最后一段有意义的作为 answer
        answer = self._extract_last_meaningful(result["raw"])
        thinking = self._extract_thinking(result["raw"], answer)
        return {"answer": answer, "thinking": thinking}

    def ask_code(self, prompt: str, language: str = "Python") -> str:
        """代码生成：引导输出代码块"""
        sys = (
            f"你是{language}专家。\n"
            "输出格式：\n"
            "```{language}\n"
            "代码\n"
            "```\n"
            "之后可以有简要说明。\n"
            "不要输出推理过程。"
        )
        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt},
        ]
        result = self._call(messages)
        
        # 提取代码块
        blocks = re.findall(
            r'```' + re.escape(language) + r'\n(.*?)```',
            result["raw"], re.DOTALL
        )
        if blocks:
            return blocks[-1].strip()
        
        # 通用代码块
        blocks = re.findall(r'```\w*\n(.*?)```', result["raw"], re.DOTALL)
        if blocks:
            return blocks[-1].strip()
        
        # fallback
        return result["raw"].strip()

    def health_check(self) -> bool:
        try:
            return len(self.ask("你好")) > 0
        except:
            return False

    def _clean_output(self, raw: str) -> str:
        """
        清理模型输出，去掉推理元信息。
        
        典型 bad output:
          "Here's a thinking process:\n1. Analyze...\n2. Plan...\nFinal Output:** "2"
        
        期望 output:
          "2"
        """
        text = raw.strip()
        
        # 如果很短，直接返回
        if len(text) <= 100:
            return text
        
        # 方法1: 找引号包裹的内容（模型常常把答案放在引号里）
        quotes = re.findall(r'"([^"]+)"', text)
        if quotes:
            # 取最后一个引号内容（通常是最终决定）
            last_quote = quotes[-1]
            if len(last_quote) <= 500:  # 合理长度
                return last_quote
        
        # 方法2: 找 "Final Output" 后面的引号内容
        m = re.search(r'Final Output[^"]*["\']([^"\']+)["\']', text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        
        # 方法3: 取最后一行非空文字
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            # 去掉含 "thinking" / "Final" / "**" 的行
            clean_lines = []
            for l in lines:
                skip = any(x in l.lower() for x in [
                    "thinking process", "here's a thinking", "here is a thinking",
                    "final output", "final answer", "let me", "好的，",
                    "check:", "verify:", "confirmation:",
                ])
                if not skip:
                    clean_lines.append(l)
            if clean_lines:
                return clean_lines[-1]
        
        # 兜底
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


# ===== 便捷函数 =====
_adapter = None
def get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = Qwen36Adapter()
    return _adapter

def ask(prompt, system=None):
    return get_adapter().ask(prompt, system)

def ask_detailed(prompt, system=None):
    return get_adapter().ask_reasoned(prompt, system)

def ask_code(prompt, language="Python"):
    return get_adapter().ask_code(prompt, language)


# ===== 测试 =====
if __name__ == "__main__":
    print("🧪 qwen3.6-35b 适配层 v5 测试")
    print("=" * 60)
    a = Qwen36Adapter()

    print("\n1. 简单问题:")
    r = a.ask("1+1等于多少？")
    print(f"   回答: {r}")
    print(f"   长度: {len(r)} | {'✅ 简洁' if len(r) < 100 else '⚠️ 偏长'}")

    print("\n2. 数学推理:")
    r = a.ask_reasoned("1/2 + 1/3 = ?")
    print(f"   回答: {r['answer'][:150]}")
    print(f"   推理: {len(r['thinking'])} 字符")

    print("\n3. 代码生成:")
    r = a.ask_code("快速排序")
    print(f"   代码: {r[:200]}")
    print(f"   长度: {len(r)}")

    print("\n4. 健康检查:", "✅" if a.health_check() else "❌")

    print("\n✅ 测试完成")
