#!/usr/bin/env python3
"""测试 zhangtuo-ai/qwen3.6-35b: content 是否总是 null，reasoning 是否有值"""

import requests
import json
import time

KEY = "sk-28PRiilecewqbNN9G1TGHhQwML6KCa8yMtvO5HH1KzuuLKbB"
BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"
MODEL = "qwen3.6-35b"

print(f"\n{'='*70}")
print(f"  🧪 测试: zhangtuo-ai/qwen3.6-35b content vs reasoning")
print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}\n")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {KEY}"
}

# 测试几个不同的 prompt
prompts = [
    "直接回答：中国首都是哪里？",
    "1+1等于几？只给数字。",
    "解释量子纠缠，100字以内。",
]

for i, prompt in enumerate(prompts, 1):
    print(f"--- Test {i}/{len(prompts)} ---")
    print(f"  问: {prompt}")
    
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.3
    }
    
    start = time.perf_counter()
    try:
        r = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=30)
        lat = (time.perf_counter() - start) * 1000
        
        if r.status_code != 200:
            print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")
            continue
        
        data = r.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content")
        reasoning = msg.get("reasoning") or ""
        
        print(f"  ⏱ {lat:.0f}ms")
        print(f"  content: type={type(content).__name__}, value={repr(content)}")
        print(f"  reasoning: {len(reasoning)} 字, 前100字: {reasoning[:100]}")
        
        if content is None or content == "":
            print(f"  ⚠️  content 为空！读取 reasoning...")
            if reasoning:
                print(f"  ✅ reasoning 有值！使用 reasoning 作为输出")
            else:
                print(f"  ❌ reasoning 也没有值！API 可能出问题了")
        else:
            print(f"  ✅ content 有值！{content[:100]}")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()

print("Done!")
