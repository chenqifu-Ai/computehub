#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4 卡 GPU 测试计划 - 阶段 2：多卡性能对比测试
（通过并发性能推断多卡配置）
"""
import requests, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://58.23.129.98:8001"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

def test_concurrency_scaling():
    """测试并发扩展性能（推断多卡能力）"""
    print("=" * 80)
    print("  📈 阶段 2：多卡性能对比测试")
    print("=" * 80)
    print("\n  测试方法：通过并发数变化推断 GPU 扩展能力\n")
    
    # 不同并发数测试
    concurrency_levels = [1, 2, 4, 8, 16, 32, 64]
    results = {}
    
    for n in concurrency_levels:
        start = time.time()
        success_count = 0
        total_elapsed = 0
        
        def make_request(req_id):
            payload = {
                "model": "qwen3.6-35b",
                "messages": [{"role": "user", "content": [{"type": "text", "text": f"并发测试{req_id}"}]}],
                "max_tokens": 100
            }
            r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return True
            return False
        
        with ThreadPoolExecutor(max_workers=n) as executor:
            futures = [executor.submit(make_request, i) for i in range(n)]
            for future in as_completed(futures):
                if future.result():
                    success_count += 1
        
        elapsed = time.time() - start
        avg_latency = elapsed / success_count if success_count > 0 else 0
        
        results[n] = {
            'success': success_count,
            'total_time': elapsed,
            'avg_latency': avg_latency,
            'throughput': success_count / elapsed if elapsed > 0 else 0
        }
        
        print(f"  并发{n}: 成功{success_count}/{n} | 总耗时{elapsed:.2f}s | 平均延迟{avg_latency:.3f}s | 吞吐{results[n]['throughput']:.1f} req/s")
        
        # 短暂间隔
        time.sleep(1)
    
    return results

def test_output_speed():
    """测试不同输出长度的速度"""
    print("\n" + "=" * 80)
    print("  🚀 输出速度测试")
    print("=" * 80)
    
    max_tokens_list = [50, 100, 500, 1000, 2000, 4000]
    
    for max_tokens in max_tokens_list:
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "请持续输出直到达到指定 tokens 数量"}]}],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        start = time.time()
        r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=120)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            usage = data.get('usage', {})
            completion_tokens = usage.get('completion_tokens', 0)
            actual_speed = completion_tokens / elapsed if elapsed > 0 else 0
            
            print(f"  输出{completion_tokens} tokens: 耗时{elapsed:.2f}s, 速度{actual_speed:.1f} tokens/s")
        else:
            print(f"  ❌ 输出{max_tokens} tokens: HTTP {r.status_code}")
    
    time.sleep(2)

def test_latency_stability():
    """测试延迟稳定性"""
    print("\n" + "=" * 80)
    print("  📊 延迟稳定性测试")
    print("=" * 80)
    
    print("\n  连续 20 次请求延迟测量...")
    latencies = []
    
    for i in range(20):
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": f"稳定测试{i}"}]}],
            "max_tokens": 50
        }
        
        start = time.time()
        r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=30)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            latencies.append(elapsed)
            status = "✅"
        else:
            status = "❌"
        
        if (i + 1) % 5 == 0:
            avg = sum(latencies) / len(latencies)
            print(f"    请求{status} 延迟{elapsed:.3f}s (最近 5 次平均：{avg:.3f}s)")
        
        time.sleep(0.5)
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        std_dev = (sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)) ** 0.5
        
        print(f"\n  📈 延迟统计：")
        print(f"    平均延迟：{avg_latency:.3f}s")
        print(f"    最小延迟：{min_latency:.3f}s")
        print(f"    最大延迟：{max_latency:.3f}s")
        print(f"    标准差：{std_dev:.3f}s (越低越稳定)")
        print(f"    稳定性评级：{'优秀' if std_dev < 0.2 else '良好' if std_dev < 0.5 else '一般'}")
    
    time.sleep(2)

def test_gpu_utilization_simulation():
    """模拟 GPU 利用率测试"""
    print("\n" + "=" * 80)
    print("  ⚡ GPU 利用率模拟测试")
    print("=" * 80)
    
    print("\n  模拟高负载场景...")
    
    # 持续发送请求模拟高负载
    start = time.time()
    success_count = 0
    
    for i in range(50):
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": f"负载测试{i}"}]}],
            "max_tokens": 200
        }
        
        r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=60)
        if r.status_code == 200:
            success_count += 1
        
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start
            throughput = success_count / elapsed if elapsed > 0 else 0
            print(f"    完成{success_count}/50 请求，耗时{elapsed:.2f}s，吞吐{throughput:.1f} req/s")
        
        time.sleep(0.3)
    
    total_elapsed = time.time() - start
    avg_throughput = success_count / total_elapsed if total_elapsed > 0 else 0
    
    print(f"\n  📊 高负载测试总结：")
    print(f"    总请求数：50")
    print(f"    成功数：{success_count}")
    print(f"    总耗时：{total_elapsed:.2f}s")
    print(f"    平均吞吐：{avg_throughput:.1f} req/s")
    print(f"    GPU 负载评估：{'高' if avg_throughput > 5 else '中' if avg_throughput > 2 else '低'}")

def main():
    print("\n🚀 开始执行阶段 2：多卡性能对比测试\n")
    
    test_concurrency_scaling()
    test_output_speed()
    test_latency_stability()
    test_gpu_utilization_simulation()
    
    print("\n" + "=" * 80)
    print("  ✅ 阶段 2 完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
