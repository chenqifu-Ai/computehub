#!/usr/bin/env python3
"""代理模型并发测试"""

import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED

PROXY_URL = "http://127.0.0.1:8765/v1/chat/completions"
MODEL = "qwen3.6-35b"

def send_request(concurrency_level, req_id):
    """发送单个请求"""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"并发测试 {req_id}，当前并发数：{concurrency_level}"}],
        "max_tokens": 50
    }
    start = time.time()
    try:
        resp = requests.post(PROXY_URL, json=payload, timeout=60)
        elapsed = time.time() - start
        return {
            "req_id": req_id,
            "success": resp.status_code == 200,
            "http_status": resp.status_code,
            "elapsed": elapsed,
            "tokens": resp.json().get("usage", {}).get("completion_tokens", 0) if resp.status_code == 200 else 0
        }
    except Exception as e:
        return {
            "req_id": req_id,
            "success": False,
            "error": str(e),
            "elapsed": time.time() - start
        }

def run_concurrent_test(concurrency):
    """执行指定并发数的测试"""
    print(f"\n{'=' * 60}")
    print(f"🔥 并发数: {concurrency}")
    print(f"{'=' * 60}")
    
    start_all = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # 提交所有任务
        futures = [executor.submit(send_request, concurrency, i) for i in range(concurrency)]
        
        # 等待全部完成
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    total_time = time.time() - start_all
    
    # 统计
    success_count = sum(1 for r in results if r["success"])
    failed_count = concurrency - success_count
    elapsed_times = [r["elapsed"] for r in results if r["success"]]
    
    if elapsed_times:
        avg = sum(elapsed_times) / len(elapsed_times)
        min_t = min(elapsed_times)
        max_t = max(elapsed_times)
        p95_idx = int(len(elapsed_times) * 0.95)
        sorted_times = sorted(elapsed_times)
        p95 = sorted_times[min(p95_idx, len(sorted_times)-1)]
        
        print(f"  总耗时: {total_time:.2f}s")
        print(f"  成功: {success_count}/{concurrency}")
        print(f"  失败: {failed_count}/{concurrency}")
        print(f"  平均延迟: {avg:.2f}s")
        print(f"  最快: {min_t:.2f}s")
        print(f"  最慢: {max_t:.2f}s")
        print(f"  P95 延迟: {p95:.2f}s")
        
        # 单个请求耗时
        print(f"\n  各请求耗时:")
        for r in sorted(results, key=lambda x: x["elapsed"]):
            status = "✅" if r["success"] else "❌"
            print(f"    {status} 请求 {r['req_id']:2d}: {r['elapsed']:.2f}s | {r.get('tokens', 0)} tokens", end="")
            if not r["success"]:
                print(f" | {r.get('error', '')}", end="")
            print()
    
    return {
        "concurrency": concurrency,
        "total_time": total_time,
        "success_count": success_count,
        "failed_count": failed_count,
        "avg_latency": avg if elapsed_times else 0,
        "max_latency": max_t if elapsed_times else 0,
        "min_latency": min_t if elapsed_times else 0,
        "p95": p95 if elapsed_times else 0
    }

def main():
    print("=" * 60)
    print("🧪 代理模型并发测试")
    print("=" * 60)
    
    # 测试不同并发数
    concurrency_levels = [1, 2, 5, 10, 15, 20]
    results = []
    
    for level in concurrency_levels:
        try:
            result = run_concurrent_test(level)
            results.append(result)
        except Exception as e:
            print(f"  ❌ 并发 {level} 测试失败: {e}")
    
    # 汇总
    print(f"\n{'=' * 60}")
    print("📊 汇总")
    print(f"{'=' * 60}")
    print(f"  {'并发数':>6s} | {'总耗时':>8s} | {'成功数':>6s} | {'平均延迟':>8s} | {'P95':>8s} | {'最慢':>8s} | {'状态'}")
    print(f"  {'-'*6}-+-{'-'*8}-+-{'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")
    
    for r in results:
        status = "✅" if r["failed_count"] == 0 else "❌"
        print(f"  {r['concurrency']:>6d} | {r['total_time']:>7.2f}s | {r['success_count']:>6d}/{r['concurrency']} | {r['avg_latency']:>7.2f}s | {r['p95']:>7.2f}s | {r['max_latency']:>7.2f}s | {status}")
    
    print(f"\n{'=' * 60}")
    print("✅ 测试完成")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
