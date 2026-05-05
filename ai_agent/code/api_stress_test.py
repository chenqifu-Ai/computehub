#!/usr/bin/env python3
"""
API 压力测试 - 简单直接版
"""
import time
import requests

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
MODEL = "qwen3.6-35b"
PROMPTS = [
    "请解释量子计算的原理。",
    "写一首关于春天的诗。",
    "分析中国经济当前形势。",
    "用Python写快速排序。",
    "描述太阳系结构。",
]

def single_request(timeout=30):
    t0 = time.monotonic()
    try:
        r = requests.post(API_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "测试"}],
            "max_tokens": 64,
        }, headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}, timeout=timeout)
        elapsed = (time.monotonic() - t0) * 1000
        if r.status_code == 200:
            data = r.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content", "") or msg.get("reasoning", "")
            print(f"  ✅ {elapsed:.0f}ms | {len(content)} 字符")
            return elapsed, len(content), True
        else:
            print(f"  ❌ {elapsed:.0f}ms | HTTP {r.status_code}")
            return elapsed, 0, False
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return 0, 0, False

print("=" * 50)
print("🔥 API 压力测试 - qwen3.6-35b")
print("=" * 50)

# 0. 单请求基准
print("\n📏 单请求基准 (5次):")
times = []
for i in range(5):
    t, c, ok = single_request(timeout=30)
    if ok:
        times.append(t)
if times:
    print(f"  平均: {sum(times)/len(times):.0f}ms | 最快: {min(times):.0f}ms | 最慢: {max(times):.0f}ms")

# 1. 小批量并发
print("\n🧪 4 并发 × 4 请求:")
t0 = time.monotonic()
threads = []
import threading
results = []
def worker(idx, prompt):
    start = time.monotonic()
    ok = False
    try:
        r = requests.post(API_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
        }, headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}, timeout=30)
        elapsed = (time.monotonic() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content", "") or msg.get("reasoning", "")
            results.append((elapsed, len(content), True))
        else:
            results.append((elapsed, 0, False))
    except Exception as e:
        results.append((0, 0, False))
        
for i in range(4):
    t = threading.Thread(target=worker, args=(i, PROMPTS[i % len(PROMPTS)]))
    t.start()
    threads.append(t)
for t in threads:
    t.join(timeout=60)
total = time.monotonic() - t0
ok = [r for r in results if r[2]]
fail = len(results) - len(ok)
if ok:
    times = [r[0] for r in ok]
    chars = [r[1] for r in ok]
    print(f"  ✅ {len(ok)}/4 成功 | 平均 {sum(times)/len(times):.0f}ms | 输出平均 {sum(chars)/len(chars):.0f} 字符")
print(f"  ❌ {fail} 失败 | 总耗时 {total:.1f}s")

# 2. 中批量并发
print("\n🧪 8 并发 × 8 请求:")
results.clear()
threads.clear()
t0 = time.monotonic()
for i in range(8):
    t = threading.Thread(target=worker, args=(i, PROMPTS[i % len(PROMPTS)]))
    t.start()
    threads.append(t)
for t in threads:
    t.join(timeout=60)
total = time.monotonic() - t0
ok = [r for r in results if r[2]]
fail = len(results) - len(ok)
if ok:
    times = [r[0] for r in ok]
    chars = [r[1] for r in ok]
    print(f"  ✅ {len(ok)}/8 成功 | 平均 {sum(times)/len(times):.0f}ms | 输出平均 {sum(chars)/len(chars):.0f} 字符")
print(f"  ❌ {fail} 失败 | 总耗时 {total:.1f}s")

# 3. 大并发
print("\n🧪 16 并发 × 16 请求:")
results.clear()
threads.clear()
t0 = time.monotonic()
for i in range(16):
    t = threading.Thread(target=worker, args=(i, PROMPTS[i % len(PROMPTS)]))
    t.start()
    threads.append(t)
for t in threads:
    t.join(timeout=45)
total = time.monotonic() - t0
ok = [r for r in results if r[2]]
fail = len(results) - len(ok)
if ok:
    times = [r[0] for r in ok]
    chars = [r[1] for r in ok]
    print(f"  ✅ {len(ok)}/16 成功 | 平均 {sum(times)/len(times):.0f}ms | 输出平均 {sum(chars)/len(chars):.0f} 字符")
print(f"  ❌ {fail} 失败 | 总耗时 {total:.1f}s")

# 4. 极限并发
print("\n🧪 32 并发 × 32 请求 (30s 超时):")
results.clear()
threads.clear()
t0 = time.monotonic()
for i in range(32):
    t = threading.Thread(target=worker, args=(i, PROMPTS[i % len(PROMPTS)]))
    t.start()
    threads.append(t)
for t in threads:
    t.join(timeout=30)
total = time.monotonic() - t0
ok = [r for r in results if r[2]]
fail = len(results) - len(ok)
if ok:
    times = [r[0] for r in ok]
    chars = [r[1] for r in ok]
    print(f"  ✅ {len(ok)}/32 成功 | 平均 {sum(times)/len(times):.0f}ms | 输出平均 {sum(chars)/len(chars):.0f} 字符")
print(f"  ❌ {fail} 失败 | 总耗时 {total:.1f}s")

print("\n" + "=" * 50)
print("✅ 测试完成")
print("=" * 50)
