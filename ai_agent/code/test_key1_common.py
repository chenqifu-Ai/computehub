#!/usr/bin/env python3
"""测试 Key1 + qwen3.6-35b-common 逐题"""

import requests
import time

KEY = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"
BASE = "https://ai.zhangtuokeji.top:9090/v1"
MODEL = "qwen3.6-35b-common"

headers = {"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}

PROMPTS = [
    "1+1等于几？",
    "鸡兔同笼，35头94脚，鸡兔各多少？",
    "写一个Python快速排序，含类型注解。",
    "Q1-Q4营收100/150/130/200万，算增长率。",
]

print(f"\n  测试: Key1 (sk-3RgMq1...) + {MODEL}")
print(f"{'─'*80}")

for i, prompt in enumerate(PROMPTS, 1):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096, "temperature": 0.7}
    
    start = time.perf_counter()
    r = requests.post(f"{BASE}/chat/completions", headers=headers, json=body, timeout=120)
    lat = (time.perf_counter() - start) * 1000
    
    if r.status_code == 200:
        data = r.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        finish = data["choices"][0].get("finish_reason", "?")
        actual = data["model"]
        
        icon = "⚡" if lat < 10000 else ("🔵" if lat < 20000 else "🐌")
        print(f"\n  T{i}: {prompt}")
        print(f"  {icon} ⏱{lat:.0f}ms | 实际模型:{actual} | 📏content={len(content)}字 🧠reasoning={len(reasoning)}字 | finish={finish}")
        print(f"  → content: {content[:100]}")
        print(f"  → reasoning: {reasoning[:100]}...")
    else:
        print(f"  T{i}: ❌ HTTP {r.status_code} {r.text[:100]}")
