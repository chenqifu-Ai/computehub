#!/usr/bin/env python3
"""测试 zhangtuo-ai/qwen3.6-35b-common (改后的)"""

import requests
import time

KEY = "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"
BASE = "https://ai.zhangtuokeji.top:9090/v1"

PROMPTS = [
    "1+1等于几？",
    "鸡兔同笼，35头94脚，各多少？",
    "写Python快速排序",
    "500字解释量子计算",
]

for model_name in ["qwen3.6-35b-common"]:
    print(f"\n📌 测试: {model_name}")
    print(f"   Key: {KEY[:15]}...")
    print(f"{'─'*80}")
    
    for i, prompt in enumerate(PROMPTS, 1):
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}
        body = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096, "temperature": 0.7}
        
        start = time.perf_counter()
        try:
            r = requests.post(f"{BASE}/chat/completions", headers=headers, json=body, timeout=120)
            lat = (time.perf_counter() - start) * 1000
            
            if r.status_code == 200:
                data = r.json()
                actual = data.get("model", "?")
                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning") or ""
                finish = data["choices"][0].get("finish_reason", "?")
                usage = data.get("usage", {})
                
                icon = "⚡" if lat < 10000 else ("🔵" if lat < 20000 else "🐌")
                print(f"\n  T{i}: {prompt}")
                print(f"  {icon} ⏱{lat:.0f}ms | 实际:{actual} | 📏{len(content)}字 🧠{len(reasoning)}字 | finish={finish}")
                print(f"  → {content[:120]}")
            else:
                print(f"  T{i}: ❌ HTTP {r.status_code} {r.text[:100]}")
        except Exception as e:
            print(f"  T{i}: ❌ {e}")
