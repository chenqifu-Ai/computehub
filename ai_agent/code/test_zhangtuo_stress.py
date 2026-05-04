#!/usr/bin/env python3
"""
zhangtuo-ai 压力并发测试
- 对比不同并发度下的成功率、延迟、吞吐量
- 同时测 A (非 common) 和 B (common)
"""

import requests
import json
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://ai.zhangtuokeji.top:9090/v1"
KEY_A = "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"
KEY_B = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"

PROMPTS = [
    "你好",
    "解释量子纠缠",
    "写一个Python快速排序",
    "计算 9999 * 8888 + 1234",
    "用Markdown列出中国美食TOP5",
]

def call(model_id, api_key, prompt):
    url = f"{BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 256,
        "temperature": 0.7
    }
    t0 = time.time()
    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        elapsed = time.time() - t0
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code, "latency_ms": round(elapsed*1000, 1), "error": r.text[:200]}
        resp = r.json()
        msg = resp["choices"][0]["message"]
        reasoning = msg.get("reasoning") or ""
        content = msg.get("content") or ""
        total_text = reasoning + content
        stop = resp["choices"][0].get("finish_reason", "?")
        usage = resp.get("usage", {})
        return {
            "ok": True,
            "latency_ms": round(elapsed*1000, 1),
            "output_chars": len(total_text),
            "total_tokens": usage.get("total_tokens", "?"),
            "stop_reason": stop,
            "reasoning_chars": len(reasoning)
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {"ok": False, "error": str(e), "latency_ms": round(elapsed*1000, 1)}

def run_batch(model_label, model_id, api_key, concurrency, prompts_per_worker):
    """Single concurrency level test for one model"""
    # Build task list
    tasks = []
    for i in range(prompts_per_worker):
        prompt = PROMPTS[i % len(PROMPTS)]
        tasks.append((model_id, api_key, prompt))
    
    total_tasks = len(tasks)
    results = []
    
    print(f"\n  [{model_label}] 并发={concurrency} | 任务数={total_tasks}")
    print(f"  {'─'*70}")
    
    success = 0
    latencies = []
    errors = []
    stops = {}
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(call, tid, tk, p): idx 
                   for idx, (tid, tk, p) in enumerate(tasks)}
        
        completed = 0
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            
            if res["ok"]:
                success += 1
                latencies.append(res["latency_ms"])
                sr = res.get("stop_reason", "unknown")
                stops[sr] = stops.get(sr, 0) + 1
            else:
                errors.append(res)
            
            # Progress bar
            pct = completed / total_tasks * 100
            bar_len = 30
            filled = int(bar_len * completed // total_tasks)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r    [{bar}] {completed}/{total_tasks} ({pct:.0f}%)", end="", flush=True)
    
    print()  # New line after progress
    
    if not latencies:
        print(f"  ❌ 全部失败!")
        for err in errors[:3]:
            print(f"     → {err['error'][:100]}")
        return None
    
    avg_lat = statistics.mean(latencies)
    med_lat = sorted(latencies)[len(latencies)//2]
    
    # TPS (tasks per second)
    all_times = [r["latency_ms"] for r in results]
    total_time_s = max(max(all_times), 100) / 1000  # Use wall clock-ish estimate
    
    # Throughput = total_tasks / (time to complete all)
    # Better estimate: measure actual wall clock time
    # For simplicity use latency-based: sum(1/latency) gives parallel throughput approximation
    
    print(f"  ✅ 成功: {success}/{total_tasks} ({success/total_tasks*100:.1f}%)")
    print(f"  ⏱️  延迟 P50: ~{med_lat:.0f}ms | 均值: {avg_lat:.0f}ms | 范围: {min(latencies):.0f}~{max(latencies):.0f}ms")
    print(f"  📝 输出长度: 平均 {statistics.mean([r['output_chars'] for r in results if r['ok']]):.0f}字符")
    print(f"  🛑 Stop: {stops}")
    if errors:
        print(f"  ❌ 失败: {len(errors)} 次")
    
    return {
        "label": model_label,
        "concurrency": concurrency,
        "total": total_tasks,
        "success": success,
        "failures": len(errors),
        "success_rate": success/total_tasks,
        "latency_p50": med_lat,
        "latency_avg": avg_lat,
        "latency_min": min(latencies),
        "latency_max": max(latencies),
        "avg_output_chars": statistics.mean([r["output_chars"] for r in results if r["ok"]]),
        "stops": stops,
        "errors": len(errors)
    }

# ============ MAIN ============
print("=" * 90)
print("🔥 zhangtuo-ai 压力并发测试")
print(f"   A: qwen3.6-35b       vs   B: qwen3.6-35b-common")
print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 90)

all_results = {"A": [], "B": []}

# Test configurations: (label, model_id, api_key, concurrencies, tasks_per_worker)
test_configs = [
    ("A — qwen3.6-35b",      "qwen3.6-35b",          KEY_A, [1, 2, 4, 8, 16], 5),
    ("B — qwen3.6-35b-common","qwen3.6-35b-common",   KEY_B, [1, 2, 4, 8, 16], 5),
]

for label, model_id, api_key, concurrencies, tasks_per_worker in test_configs:
    print(f"\n{'━' * 90}")
    print(f"🧪 测试组: {label}")
    print(f"   提示词池: {len(PROMPTS)} 个 | 每并发任务: {tasks_per_worker} 个")
    
    for concurrency in concurrencies:
        res = run_batch(label, model_id, api_key, concurrency, tasks_per_worker)
        if res:
            all_results["A" if label.startswith("A") else "B"].append(res)

# Summary table
print(f"\n{'='*90}")
print("📊 汇总对比表")
print(f"{'='*90}")
print(f"\n{'并发':>6} | {'A 成功率':>10} | {'B 成功率':>10} | {'A P50':>8} | {'B P50':>8} | {'A 失败':>6} | {'B 失败':>6}")
print(f"{'─'*80}")

concurrencies = sorted(set(r["concurrency"] for r in all_results["A"]))
for c in concurrencies:
    ra = next((r for r in all_results["A"] if r["concurrency"] == c), None)
    rb = next((r for r in all_results["B"] if r["concurrency"] == c), None)
    
    a_sr = f"{ra['success_rate']*100:.1f}%" if ra else "N/A"
    b_sr = f"{rb['success_rate']*100:.1f}%" if rb else "N/A"
    a_p50 = f"{ra['latency_p50']:.0f}ms" if ra else "-"
    b_p50 = f"{rb['latency_p50']:.0f}ms" if rb else "-"
    a_f = str(ra["failures"]) if ra else "-"
    b_f = str(rb["failures"]) if rb else "-"
    
    marker_a = " 🟢" if ra and ra["success_rate"] == 1.0 else " 🔴" if ra else ""
    marker_b = " 🟢" if rb and rb["success_rate"] == 1.0 else " 🔴" if rb else ""
    
    print(f"{c:>6} | {a_sr:>10}{marker_a} | {b_sr:>10}{marker_b} | {a_p50:>8} | {b_p50:>8} | {a_f:>6} | {b_f:>6}")

# Key insights
print(f"\n{'='*90}")
print("💡 关键发现")
print(f"{'='*90}")

best_a = min(all_results["A"], key=lambda x: x["latency_p50"]) if all_results["A"] else None
best_b = min(all_results["B"], key=lambda x: x["latency_p50"]) if all_results["B"] else None

if best_a and best_b:
    print(f"  A 最低延迟 P50: {best_a['latency_p50']:.0f}ms (并发={best_a['concurrency']})")
    print(f"  B 最低延迟 P50: {best_b['latency_p50']:.0f}ms (并发={best_b['concurrency']})")
    
    if best_b["latency_p50"] < best_a["latency_p50"]:
        diff = ((best_a["latency_p50"] - best_b["latency_p50"]) / best_a["latency_p50"] * 100)
        print(f"  B 比 A 快 {diff:.1f}%")
    else:
        diff = ((best_b["latency_p50"] - best_a["latency_p50"]) / best_b["latency_p50"] * 100)
        print(f"  A 比 B 快 {diff:.1f}%")

# Check for degradation at high concurrency
for tag, label in [("A", "A"), ("B", "B")]:
    res_list = all_results[tag]
    if len(res_list) >= 2:
        low_conc_success = min(r["success_rate"] for r in res_list if r["concurrency"] <= 4)
        high_conc_failures = max(r["failures"] for r in res_list if r["concurrency"] > 4)
        if high_conc_failures > 0:
            worst_c = max(res_list, key=lambda x: x["concurrency"])
            print(f"  {label}: 高并发({worst_c['concurrency']})出现退化! 失败{worst_c['failures']}次, 成功率{worst_c['success_rate']*100:.1f}%")

print(f"\n{'='*90}")
print("✅ 测试完成")
print(f"{'='*90}")
