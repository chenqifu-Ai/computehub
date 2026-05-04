#!/usr/bin/env python3
"""测试 zhangtuo-ai/qwen3.6-35b-common 模型"""

import requests
import json
import time
from datetime import datetime

KEY = "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"
BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"
MODEL = "qwen3.6-35b-common"

PROMPTS = [
    "你是谁？请简短回答。",
    "鸡兔同笼，35头94脚，鸡兔各多少？给出计算过程。",
    "写一个Python快速排序，含类型注解。",
    "所有猫会爬树，汤姆是猫，汤姆能爬树？分析推理。",
]

print(f"\n{'='*80}")
print(f"  🧪 测试: zhangtuo-ai/qwen3.6-35b-common")
print(f"  Key: sk-1G7n...")
print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {KEY}"
}

for i, prompt in enumerate(PROMPTS, 1):
    print(f"--- 测试 {i}/{len(PROMPTS)} ---")
    print(f"  问题: {prompt}")
    
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.7
    }
    
    start = time.perf_counter()
    try:
        r = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=120)
        lat = (time.perf_counter() - start) * 1000
        
        if r.status_code != 200:
            print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")
            continue
        
        data = r.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        finish = data["choices"][0].get("finish_reason", "?")
        usage = data.get("usage", {})
        
        print(f"  ⏱ 延迟: {lat:.0f}ms")
        print(f"  📏 content: {len(content)} 字")
        print(f"  🧠 reasoning: {len(reasoning)} 字")
        print(f"  🏁 finish: {finish}")
        print(f"  🔤 使用: prompt={usage.get('prompt_tokens',0)} → completion={usage.get('completion_tokens',0)} (总={usage.get('total_tokens',0)})")
        
        if content:
            display = content[:150] + ("..." if len(content) > 150 else "")
            print(f"  💬 content: {display}")
        else:
            print(f"  ⚠️ content 为空! reasoning: {reasoning[:100]}")
            
    except Exception as e:
        print(f"  ❌ 异常: {e}")
    
    print()

print(f"{'='*80}")
