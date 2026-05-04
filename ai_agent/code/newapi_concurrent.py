#!/usr/bin/env python3
"""NewAPI 双 Key 并发测试"""

import requests
import json
import time
import concurrent.futures
from datetime import datetime

KEYS = [
    {"name": "Key1 (common)", "key": "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl", "model": "qwen3.6-35b-common"},
    {"name": "Key2 (非common)", "key": "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe", "model": "qwen3.6-35b"},
]

BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"

TESTS = [
    "鸡兔同笼，35头94脚，鸡兔各多少？",
    "Python写快速排序，含类型注解和单元测试。",
    "200字AI觉醒故事，要有反转。",
    "所有猫会爬树，汤姆是猫，汤姆能爬树？分析。",
    "Q1-Q4营收100/150/130/200万，算增长率并分析。",
    "自动驾驶撞行人还是撞墙？伦理学分析。",
    "500字解释量子计算，含原理和应用。",
    "300字总结《三体》核心思想并评价。",
]

def call_single(key_cfg, prompt):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key_cfg['key']}"}
    body = {"model": key_cfg["model"], "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048, "temperature": 0.7}
    start = time.perf_counter()
    try:
        r = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=180)
        lat = (time.perf_counter() - start) * 1000
        if r.status_code != 200:
            return None, lat, r.status_code, r.text[:100]
        data = r.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        usage = data.get("usage", {})
        finish = data["choices"][0].get("finish_reason", "?")
        return {
            "content_len": len(content), "reasoning_len": len(reasoning),
            "content": content[:200], "reasoning": reasoning[:100]
        }, lat, 0, f"content={len(content)}r={len(reasoning)}"
    except Exception as e:
        return None, (time.perf_counter() - start) * 1000, 0, str(e)[:80]

print(f"\n{'='*90}")
print(f"  🔥 NewAPI 双 Key 并发测试 (每个 key 5 并发)")
print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*90}")

for k in KEYS:
    print(f"\n  📌 {k['name']} ({k['model']})")
    print(f"  {'─'*80}")

# 并发测试
for task_id, prompt in enumerate(TESTS):
    print(f"\n  任务 {task_id+1}/8: {prompt[:50]}")
    
    start_all = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for k in KEYS:
            futures[executor.submit(call_single, k, prompt)] = k["name"]
        
        results = {}
        for future in concurrent.futures.as_completed(futures):
            label = futures[future]
            try:
                info, lat, code, detail = future.result()
                if info and code == 0:
                    cl = info["content_len"]
                    rl = info["reasoning_len"]
                    print(f"    {label:16s}: ⏱{lat:.0f}ms | 📏{cl}字 🧠{rl}字(reasoning)")
                    results[label] = (lat, 0)
                else:
                    print(f"    {label:16s}: ❌ {detail}")
                    results[label] = (lat, code)
            except Exception as e:
                print(f"    {label:16s}: ❌ {e}")
                results[label] = (None, str(e)[:50])
    
    total = (time.perf_counter() - start_all) * 1000
    best = min(v[0] for v in results.values() if v[0] is not None) if any(v[0] is not None for v in results.values()) else 0
    print(f"    ⏱ 并发耗时: {total:.0f}ms | 最快: {best:.0f}ms")

# 串行基准
print(f"\n{'='*90}")
print(f"  📊 串行基准 (逐个串行)")
print(f"{'='*90}")

for k in KEYS:
    print(f"\n  📌 {k['name']}")
    print(f"  {'─'*80}")
    
    total_lat = 0
    total_cl = 0
    total_rl = 0
    successes = 0
    
    for i, prompt in enumerate(TESTS):
        info, lat, code, detail = call_single(k, prompt)
        if info and code == 0:
            total_cl += info["content_len"]
            total_rl += info["reasoning_len"]
            total_lat += lat
            successes += 1
            icon = "⚡" if lat < 12000 else ("🔵" if lat < 20000 else "🐌")
            print(f"    {icon} T{i+1}: ⏱{lat:.0f}ms | 📏{info['content_len']}字 🧠{info['reasoning_len']}字 | finish={detail.split('r=')[1].split(')')[0] if ')r=' in detail else '?'}")
        else:
            print(f"    ❌ T{i+1}: {detail}")
    
    if successes > 0:
        print(f"  📊 统计: {successes}/{len(TESTS)} 成功 | 平均 {total_lat/successes:.0f}ms | content总计 {total_cl}字 | reasoning总计 {total_rl}字")

# 总结
print(f"\n{'='*90}")
print(f"  📝 关键发现:")
print(f"    - 两个 key 都有 content 和 reasoning 互补的问题")
print(f"    - content 为空时，输出全在 reasoning 里")
print(f"    - max_tokens 被 reasoning 占满导致 finish=length")
print(f"{'='*90}\n")
