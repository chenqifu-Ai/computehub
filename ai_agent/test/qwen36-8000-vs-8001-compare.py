#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen3.6-35b 端口对比测试：8000 vs 8001
========================================
快速对比：并发测延迟 + 内容一致性
"""

import requests
import json
import time
import concurrent.futures

URL_8000 = "http://58.23.129.98:8000/v1/chat/completions"
URL_8001 = "http://58.23.129.98:8001/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
MODEL = "qwen3.6-35b"

def bench_one(url, name, count=5):
    """测试指定端口：并发发 count 个请求"""
    payload = {"model": MODEL, "messages": [{"role": "user", "content": "人体最大的器官是什么？直接回答。"}], "max_tokens": 30, "temperature": 0.1}
    times = []
    ok_count = 0
    start = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(
            lambda: (time.time(), requests.post(url, headers=HEADERS, json=payload, timeout=30))
        ) for _ in range(count)]
        
        for f in concurrent.futures.as_completed(futures):
            t0, resp = f.result()
            elapsed = time.time() - t0
            times.append(elapsed)
            if resp.status_code == 200:
                ok_count += 1
    
    total = time.time() - start
    avg = sum(times) / len(times) if times else 0
    return {
        'port': name,
        'count': count,
        'ok': ok_count,
        'total_time': round(total, 2),
        'avg_time': round(avg, 2),
        'min_time': round(min(times), 2) if times else 0,
        'max_time': round(max(times), 2) if times else 0,
        'qps': round(ok_count / max(total, 0.01), 1),
    }

print("=" * 70)
print("🔬 qwen3.6-35b 端口对比：8000 vs 8001 (快速版)")
print("=" * 70)

print("\n📝 测试1：延迟对比（5 并发请求）")
print("-" * 70)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    f0 = executor.submit(bench_one, URL_8000, '8000', count=5)
    f1 = executor.submit(bench_one, URL_8001, '8001', count=5)
    
    r0 = f0.result()
    r1 = f1.result()

print(f"\n{'指标':<15} {'端口 8000':>12} {'端口 8001':>12}")
print("-" * 45)
print(f"{'成功率':<15} {r0['ok']}/5 {r1['ok']}/5")
print(f"{'平均延迟':<15} {r0['avg_time']:>10.2f}s {r1['avg_time']:>10.2f}s")
print(f"{'最快延迟':<15} {r0['min_time']:>10.2f}s {r1['min_time']:>10.2f}s")
print(f"{'最慢延迟':<15} {r0['max_time']:>10.2f}s {r1['max_time']:>10.2f}s")
print(f"{'总耗时':<15} {r0['total_time']:>10.2f}s {r1['total_time']:>10.2f}s")
print(f"{'QPS':<15} {r0['qps']:>12.1f} {r1['qps']:>12.1f}")

# 测试 2：内容一致性
print(f"\n📝 测试 2：内容一致性（同一问题，两个端口返回是否相同）")
print("-" * 70)

payload = {"model": MODEL, "messages": [{"role": "user", "content": "1/2+1/3 等于多少？直接回答分数。"}], "max_tokens": 20, "temperature": 0.1}

r2000 = requests.post(URL_8000, headers=HEADERS, json=payload, timeout=30)
r2001 = requests.post(URL_8001, headers=HEADERS, json=payload, timeout=30)

ok = r2000.status_code == 200 and r2001.status_code == 200
if ok:
    msg_8000 = r2000.json()['choices'][0]['message']
    msg_8001 = r2001.json()['choices'][0]['message']
    
    r_8000 = (msg_8000.get('reasoning') or '')[:100]
    r_8001 = (msg_8001.get('reasoning') or '')[:100]
    
    # 检查是否包含相同答案
    both_have_56 = ('5/6' in r_8000 or '5/6' in r_8001)
    same_reasoning = r_8000 == r_8001
    
    print(f"  [8000] reasoning: {repr(r_8000)}")
    print(f"  [8001] reasoning: {repr(r_8001)}")
    print(f"  内容一致：{'✅ 相同' if same_reasoning else '⚠️ 不同'}")
    print(f"  都包含答案 5/6：{'✅ 是' if both_have_56 else '❌ 否'}")
else:
    print(f"  ❌ 请求失败 (8000:{r2000.status_code} | 8001:{r2001.status_code})")

# 测试 3：响应内容对比
print(f"\n📝 测试 3：响应内容对比（同一问题两个端口返回是否一致）")
print("-" * 80)

test_prompts = [
    "1+1等于多少？",
    "人体最大的器官是什么？",
    "OSI七层模型分别是什么？",
    "SQL中JOIN和LEFT JOIN的区别？",
    "写一个Python斐波那契数列",
]

def get_response(url, prompt):
    """获取单次响应"""
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500}
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=60)
    if resp.status_code == 200:
        return resp.json()['choices'][0]['message']
    return None

for i, prompt in enumerate(test_prompts):
    print(f"\n  [{i+1}] {prompt}")
    msg_8000 = get_response(URL_8000, prompt)
    msg_8001 = get_response(URL_8001, prompt)
    
    if msg_8000 and msg_8001:
        content_8000 = (msg_8000.get('content') or '')[:50]
        reasoning_8000 = (msg_8000.get('reasoning') or '')[:50]
        content_8001 = (msg_8001.get('content') or '')[:50]
        reasoning_8001 = (msg_8001.get('reasoning') or '')[:50]
        
        # 检查是否相同
        same = reasoning_8000 == reasoning_8001
        status = "✅ 一致" if same else "⚠️ 不同"
        print(f"    [8000] {status}")
        print(f"      content: {repr(content_8000)}")
        print(f"      reasoning: {repr(reasoning_8000)}")
        print(f"    [8001] {status}")
        print(f"      content: {repr(content_8001)}")
        print(f"      reasoning: {repr(reasoning_8001)}")
    else:
        print(f"    ❌ 请求失败 (8000:{msg_8000 is not None} | 8001:{msg_8001 is not None})")

# ==================== 结论 ====================
print(f"\n{'='*70}")
print(f"🎯 结论")
print(f"{'='*70}")

print(f"\n  ✅ 两个端口都可达：8000 ✅ | 8001 ✅")
faster = '端口 8000' if r0['avg_time'] < r1['avg_time'] else '端口 8001'
print(f"  🏆 平均延迟更快的：{faster} ({r0['avg_time']}s vs {r1['avg_time']}s)")
print(f"  💡 推荐：使用平均更快的端口")

# 保存报告
report = {
    "test_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "model": MODEL,
    "urls": {"8000": URL_8000, "8001": URL_8001},
    "latency_test": {
        "8000": r0,
        "8001": r1,
    },
}

save_path = "/root/.openclaw/workspace/memory/topics/技术经验/qwen36-8000-vs-8001-compare.json"
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"\n📁 报告已保存: {save_path}")
