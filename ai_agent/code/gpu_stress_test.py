#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 压力测试 - 测试 58.23.129.98:8000 极限并发
"""
import requests, json, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

BASE_URL = "http://58.23.129.98:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-78sadn09bjawde123e"
}

lock = threading.Lock()
stats = {'total': 0, 'ok': 0, 'fail': 0, 'tokens': 0}

def req(n):
    texts = ["你好", "请详细描述人工智能的未来发展趋势，包括深度学习、强化学习、自动驾驶等领域的应用前景和挑战。", "这是一个中等长度的测试。请详细描述你的思考过程。"]
    text = texts[n % 3]
    try:
        r = requests.post(f"{BASE_URL}/v1/chat/completions", json={
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "max_tokens": 500, "temperature": 0.7
        }, headers=HEADERS, timeout=60)
        ok = r.status_code == 200
        t = r.json().get("usage", {}).get("completion_tokens", 0) if ok else 0
        with lock:
            stats['total'] += 1
            if ok: stats['ok'] += 1; stats['tokens'] += t
            else: stats['fail'] += 1
        return ok
    except:
        with lock: stats['total'] += 1; stats['fail'] += 1
        return False

def test(c, dur=20):
    print(f"\n{'='*60}")
    print(f"  🔥 并发 {c} — 测试 {dur}s")
    print(f"{'='*60}")
    stats['total'] = stats['ok'] = stats['fail'] = stats['tokens'] = 0
    t0 = time.time()
    done = 0
    while time.time() - t0 < dur:
        rem = dur - (time.time() - t0)
        if rem < 1: break
        with ThreadPoolExecutor(c) as ex:
            fs = [ex.submit(req, done + i) for i in range(c)]
            for f in as_completed(fs):
                try: f.result()
                except: pass
                done += 1
        e = time.time() - t0
        print(f"  ⏱ {e:.0f}s | 请求: {stats['total']} | ✅ {stats['ok']} | ❌ {stats['fail']} | tokens: {stats['tokens']}", flush=True)
    el = time.time() - t0
    sr = stats['ok'] / stats['total'] * 100 if stats['total'] else 0
    print(f"  📊 结果: 并发={c} 总请求={stats['total']} 成功={stats['ok']} 失败={stats['fail']} 成功率={sr:.1f}% 延迟={el:.1f}s tok/s={stats['tokens']/el:.0f}", flush=True)
    return {'c': c, 'ok': stats['ok'], 'fail': stats['fail'], 'total': stats['total'], 'sr': sr, 'tokens': stats['tokens'], 'time': el}

results = []
for c in [1, 4, 8, 16, 32, 64, 100, 128]:
    r = test(c, dur=20)
    results.append(r)
    if r['sr'] < 50:
        print(f"\n  ⚠️ 并发 {c} 成功率 {r['sr']:.1f}% < 50%，提前终止", flush=True)
        break
    time.sleep(1)

print(f"\n{'='*60}")
print(f"  📊 GPU 压力测试汇总")
print(f"{'='*60}")
print(f"  {'并发':<8} {'成功率':<12} {'成功':<8} {'失败':<8} {'tok/s':<10} {'状态'}")
print(f"  {'-'*55}")
for r in results:
    s = "✅" if r['sr'] >= 95 else ("⚠️" if r['sr'] >= 80 else ("🔶" if r['sr'] >= 50 else "🔴"))
    print(f"  {r['c']:<8} {r['sr']:<10.1f}%  {r['ok']:<8} {r['fail']:<8} {r['tokens']/r['time']:<9.0f} {s}")

best = max(results, key=lambda r: r['tokens']/r['time'] if r['sr'] >= 90 else 0)
print(f"\n  🏆 最佳并发: {best['c']} (tok/s={best['tokens']/best['time']:.0f}, 成功率={best['sr']:.1f}%)")
print(f"\n  ✅ GPU 压力测试完成")
