#!/usr/bin/env python3
"""分析 qwen3.6-35b-common 的 reasoning 字段结构"""
import json, urllib.request, time

BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"
API_KEY = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"

def call_model(prompt, max_tokens=512):
    data = json.dumps({
        "model": "qwen3.6-35b-common",
        "messages": [
            {"role": "system", "content": "你是一个简洁高效的助手，直接回答问题。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        msg = body["choices"][0]["message"]
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning", "") or ""
        usage = body.get("usage", {})
        return {"content": content, "reasoning": reasoning, "usage": usage}

tests = [
    "1+1等于多少？",
    "北京和上海哪个城市人口更多？",
    "写一个 Python 快速排序函数",
    "用一句话解释量子纠缠",
]

for prompt in tests:
    result = call_model(prompt)
    reasoning = result["reasoning"]
    
    print(f"\n{'='*60}")
    print(f"Prompt: {prompt}")
    print(f"content: {repr(result['content'][:100])}")
    print(f"reasoning length: {len(reasoning)}")
    print(f"\n--- reasoning 前 200 字 ---")
    print(reasoning[:200])
    print(f"\n--- reasoning 后 200 字 ---")
    print(reasoning[-200:])
    print(f"\n--- reasoning 完整 ---")
    print(reasoning)
