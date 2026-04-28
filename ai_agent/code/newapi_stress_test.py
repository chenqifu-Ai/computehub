#!/usr/bin/env python3
"""NewAPI 并发压力测试 - 不同并发度"""

import requests
import json
import time
import concurrent.futures
from datetime import datetime

KEY = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"
BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"
MODEL = "qwen3.6-35b-common"

PROMPTS = [
    "鸡兔同笼，35头94脚，鸡兔各多少？",
    "Python写快速排序，含类型注解和单元测试。",
    "200字AI觉醒故事，要有反转。",
    "所有猫会爬树，汤姆是猫，汤姆能爬树？分析。",
    "Q1-Q4营收100/150/130/200万，算增长率并分析。",
    "自动驾驶撞行人还是撞墙？伦理学分析。",
    "500字解释量子计算，含原理和应用。",
    "300字总结《三体》核心思想并评价。",
]

def _call_api(key, model, prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.7
    }
    start = time.perf_counter()
    try:
        r = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=300)
        lat = (time.perf_counter() - start) * 1000
        if r.status_code != 200:
            return {'success': False, 'lat': lat, 'status': f"HTTP {r.status_code}"}
        data = r.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        finish = data["choices"][0].get("finish_reason", "?")
        usage = data.get("usage", {})
        return {
            'success': True,
            'lat': lat,
            'status': f"✅ {lat:.0f}ms",
            'content_len': len(content),
            'reasoning_len': len(reasoning),
            'finish': finish,
            'prompt_tokens': usage.get('prompt_tokens', 0),
            'completion_tokens': usage.get('completion_tokens', 0),
        }
    except Exception as e:
        lat = (time.perf_counter() - start) * 1000
        return {'success': False, 'lat': lat, 'status': f"❌ {str(e)[:40]}"}


CONCURRENCY_LEVELS = [1, 2, 4, 8, 16]
RESULTS = {}

print(f"\n{'='*100}")
print(f"  🔥 NewAPI 并发压力测试")
print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*100}\n")

for level in CONCURRENCY_LEVELS:
    print(f"{'─'*100}")
    print(f"  并发度: {level}")
    print(f"{'─'*100}")
    
    all_lats = []
    successes = 0
    content_empty = 0
    total_content = 0
    total_reasoning = 0
    
    start_all = time.perf_counter()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=level) as executor:
        # 每轮跑4个任务，跑2轮 = 8个请求
        all_futures = []
        for i in range(2):
            for j, prompt in enumerate(PROMPTS[:4]):
                future = executor.submit(_call_api, KEY, MODEL, prompt)
                all_futures.append((future, f"R{i+1}-{j+1}"))
        
        for future, label in all_futures:
            try:
                result = future.result(timeout=300)
                all_lats.append(result['lat'])
                if result['success']:
                    successes += 1
                    total_content += result.get('content_len', 0)
                    total_reasoning += result.get('reasoning_len', 0)
                    if result.get('content_len', 0) == 0:
                        content_empty += 1
                print(f"    {label}: {result['status']}")
            except Exception as e:
                print(f"    {label}: ❌ {str(e)[:60]}")
    
    total_time = (time.perf_counter() - start_all) * 1000
    avg_lat = sum(all_lats) / len(all_lats) if all_lats else 0
    min_lat = min(all_lats) if all_lats else 0
    max_lat = max(all_lats) if all_lats else 0
    qps = successes / (total_time / 1000) if total_time > 0 else 0
    
    RESULTS[level] = {
        'total_time': total_time,
        'avg_latency': avg_lat,
        'min_latency': min_lat,
        'max_latency': max_lat,
        'success_rate': f"{successes}/8",
        'qps': qps,
        'content_empty': content_empty,
        'avg_content': total_content / max(successes, 1),
        'avg_reasoning': total_reasoning / max(successes, 1),
    }
    
    print(f"\n  📊 结果: 总耗时 {total_time:.0f}ms | 平均延迟 {avg_lat:.0f}ms | 范围 {min_lat:.0f}-{max_lat:.0f}ms")
    print(f"       成功 {successes}/8 | QPS {qps:.2f} | content为空 {content_empty}次 | 平均content {avg_lat:.0f}ms")
    if successes > 0:
        print(f"       平均content: {total_content/successes:.0f}字 | 平均reasoning: {total_reasoning/successes:.0f}字")

# 总结报告
print(f"\n\n{'='*100}")
print(f"  📋 汇总报告")
print(f"{'='*100}")
print(f"{'并发度':>6s} | {'总耗时':>10s} | {'平均延迟':>10s} | {'最小延迟':>10s} | {'最大延迟':>10s} | {'成功率':>8s} | {'QPS':>6s} | {'content空':>8s}")
print(f"{'─'*100}")
for level in CONCURRENCY_LEVELS:
    r = RESULTS[level]
    print(f"{level:>6d} | {r['total_time']:>9.0f}ms | {r['avg_latency']:>9.0f}ms | {r['min_latency']:>9.0f}ms | {r['max_latency']:>9.0f}ms | {r['success_rate']:>8s} | {r['qps']:>6.2f} | {r['content_empty']:>8d}")
print(f"{'='*100}\n")

# 最佳并发度
best_qps = max(RESULTS.items(), key=lambda x: x[1]['qps'])
print(f"  🏆 最佳并发度: {best_qps[0]} (QPS: {best_qps[1]['qps']:.2f})")
print(f"{'='*100}\n")
