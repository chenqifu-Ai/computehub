#!/usr/bin/env python3
"""代理模型压力测试"""

import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

PROXY_URL = "http://127.0.0.1:8765/v1/chat/completions"
MODEL = "qwen3.6-35b"

def send_request(req_id):
    """发送单个请求"""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"压力测试 {req_id}"}],
        "max_tokens": 30
    }
    start = time.time()
    try:
        resp = requests.post(PROXY_URL, json=payload, timeout=120)
        elapsed = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            return {
                "req_id": req_id,
                "success": True,
                "http_status": resp.status_code,
                "elapsed": elapsed,
                "tokens": usage.get("completion_tokens", 0)
            }
        else:
            return {
                "req_id": req_id,
                "success": False,
                "http_status": resp.status_code,
                "elapsed": time.time() - start,
                "error": f"HTTP {resp.status_code}"
            }
    except Exception as e:
        return {
            "req_id": req_id,
            "success": False,
            "error": str(e),
            "elapsed": time.time() - start
        }

def run_pressure_test(concurrency):
    """执行压力测试"""
    print(f"\n{'='*70}")
    print(f"🔥 压力测试: 并发 {concurrency}")
    print(f"{'='*70}")
    
    start_all = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, i) for i in range(concurrency)]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    total_time = time.time() - start_all
    
    # 统计
    success_count = sum(1 for r in results if r["success"])
    failed_count = concurrency - success_count
    
    success_results = [r for r in results if r["success"]]
    times = [r["elapsed"] for r in success_results]
    
    if times:
        avg = statistics.mean(times)
        median = statistics.median(times)
        min_t = min(times)
        max_t = max(times)
        stdev = statistics.stdev(times) if len(times) > 1 else 0
        
        sorted_times = sorted(times)
        p50 = sorted_times[int(len(sorted_times) * 0.50)]
        p90 = sorted_times[int(len(sorted_times) * 0.90)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        # TPS
        tps = len(success_results) / total_time
        
        print(f"\n  总耗时:      {total_time:.2f}s")
        print(f"  成功率:      {success_count}/{concurrency} ({success_count/concurrency*100:.1f}%)")
        print(f"  TPS:         {tps:.2f} 请求/秒")
        print(f"\n  延迟统计:")
        print(f"    平均:      {avg:.2f}s")
        print(f"    中位数:    {median:.2f}s")
        print(f"    P50:       {p50:.2f}s")
        print(f"    P90:       {p90:.2f}s")
        print(f"    P95:       {p95:.2f}s")
        print(f"    P99:       {p99:.2f}s")
        print(f"    最快:      {min_t:.2f}s")
        print(f"    最慢:      {max_t:.2f}s")
        print(f"    标准差:    {stdev:.2f}s")
        
        if failed_count > 0:
            print(f"\n  ❌ 失败请求 {failed_count}/{concurrency}:")
            for r in results:
                if not r["success"]:
                    print(f"    请求 {r['req_id']:3d}: {r.get('error', 'timeout')} ({r['elapsed']:.2f}s)")
        
        return {
            "concurrency": concurrency,
            "total_time": total_time,
            "success_count": success_count,
            "failed_count": failed_count,
            "avg_latency": avg,
            "p90": p90,
            "p95": p95,
            "p99": p99,
            "max_latency": max_t,
            "tps": tps
        }
    else:
        print(f"  ❌ 全部失败 ({concurrency}/{concurrency})")
        return {
            "concurrency": concurrency,
            "total_time": total_time,
            "success_count": 0,
            "failed_count": concurrency,
            "tps": 0
        }

def main():
    print("="*70)
    print("🚀 代理模型压力测试")
    print("="*70)
    
    # 压力测试规模
    concurrency_levels = [50, 100, 150, 200]
    results = []
    
    for level in concurrency_levels:
        try:
            print(f"\n{'#'*70}")
            print(f"⏱  开始测试并发 {level}")
            print(f"{'#'*70}")
            result = run_pressure_test(level)
            results.append(result)
        except KeyboardInterrupt:
            print("\n\n⚠️ 测试被中断")
            break
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            break
    
    # 汇总报告
    print(f"\n{'='*70}")
    print("📊 压力测试汇总报告")
    print(f"{'='*70}")
    
    print(f"\n{'并发数':>8s} | {'总耗时':>8s} | {'成功':>8s} | {'成功率':>8s} | {'TPS':>8s} | {'P90':>8s} | {'P95':>8s} | {'P99':>8s} | {'状态'}")
    print(f"  {'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")
    
    for r in results:
        status = "✅" if r["failed_count"] == 0 else ("⚠️" if r["failed_count"] < 5 else "❌")
        print(f"  {r['concurrency']:>8d} | {r['total_time']:>7.2f}s | {r['success_count']:>8d} | {r['success_count']/r['concurrency']*100:7.1f}% | {r['tps']:>7.2f} | {r.get('p90',0):>7.2f}s | {r.get('p95',0):>7.2f}s | {r.get('p99',0):>7.2f}s | {status}")
    
    # 结论
    print(f"\n{'='*70}")
    print("🎯 测试结论")
    print(f"{'='*70}")
    
    stable = [r for r in results if r["failed_count"] == 0]
    if stable:
        max_stable = max(stable, key=lambda x: x["concurrency"])
        print(f"  ✅ 稳定运行最大并发: {max_stable['concurrency']}")
        print(f"  ✅ 最佳 TPS: {max_stable['tps']:.2f} 请求/秒")
        print(f"  ✅ P95 延迟: {max_stable['p95']:.2f}s")
    else:
        print(f"  ❌ 所有并发级别都有失败")
        min_fail = min(results, key=lambda x: x["failed_count"])
        print(f"  ⚠️ 最低失败率: {min_fail['concurrency']} 并发 ({min_fail['failed_count']}/{min_fail['concurrency']})")
    
    print(f"\n{'='*70}")
    print("✅ 测试完成")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
