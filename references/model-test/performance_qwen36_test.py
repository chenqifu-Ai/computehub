#!/usr/bin/env python3
"""
Qwen 3.6 35B 性能压力测试
测试模型的并发性能和稳定性
"""

import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

def performance_test():
    """性能压力测试"""
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    print("⚡ Qwen 3.6 35B 性能压力测试")
    print("=" * 60)
    
    # 测试配置
    test_configs = [
        {"name": "单请求基准", "concurrency": 1, "requests": 5, "prompt": "你好，请做一下自我介绍。"},
        {"name": "低并发测试", "concurrency": 3, "requests": 9, "prompt": "什么是机器学习？"},
        {"name": "中并发测试", "concurrency": 5, "requests": 15, "prompt": "解释深度学习的基本概念。"},
        {"name": "高并发测试", "concurrency": 8, "requests": 24, "prompt": "写一个简短的Python函数示例。"}
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    overall_results = []
    
    for config in test_configs:
        print(f"\n🔧 {config['name']}")
        print(f"   并发数: {config['concurrency']} | 请求数: {config['requests']}")
        
        results = []
        errors = 0
        
        def make_request(request_id):
            """单个请求函数"""
            payload = {
                "model": "qwen3.6-35b",
                "messages": [{"role": "user", "content": config["prompt"]}],
                "max_tokens": 200,
                "temperature": 0.3,
                "stream": False
            }
            
            start_time = time.time()
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=25)
                end_time = time.time()
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "time": (end_time - start_time) * 1000,
                        "tokens": result.get('usage', {}).get('total_tokens', 0),
                        "response": result['choices'][0]['message']['content'][:50] + "..."
                    }
                else:
                    return {
                        "success": False,
                        "time": (end_time - start_time) * 1000,
                        "error": f"HTTP {response.status_code}"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "time": (time.time() - start_time) * 1000,
                    "error": str(e)
                }
        
        # 执行并发测试
        start_test_time = time.time()
        
        with ThreadPoolExecutor(max_workers=config["concurrency"]) as executor:
            futures = [executor.submit(make_request, i) for i in range(config["requests"])]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                if not result["success"]:
                    errors += 1
        
        end_test_time = time.time()
        
        # 分析结果
        success_results = [r for r in results if r["success"]]
        
        if success_results:
            times = [r["time"] for r in success_results]
            tokens = [r["tokens"] for r in success_results]
            
            stats = {
                "total_time": (end_test_time - start_test_time) * 1000,
                "avg_time": statistics.mean(times),
                "min_time": min(times),
                "max_time": max(times),
                "std_time": statistics.stdev(times) if len(times) > 1 else 0,
                "avg_tokens": statistics.mean(tokens),
                "success_rate": len(success_results) / len(results) * 100,
                "throughput": len(success_results) / ((end_test_time - start_test_time) / 60)  # 请求/分钟
            }
            
            print(f"   ✅ 成功率: {stats['success_rate']:.1f}% ({len(success_results)}/{len(results)})")
            print(f"   ⏱️  平均响应: {stats['avg_time']:.0f}ms (min: {stats['min_time']:.0f}ms, max: {stats['max_time']:.0f}ms)")
            print(f"   📊 吞吐量: {stats['throughput']:.1f} 请求/分钟")
            print(f"   🔢 平均Token: {stats['avg_tokens']:.0f}")
            
            if errors > 0:
                print(f"   ❌ 错误数: {errors}")
                
        else:
            print(f"   ❌ 全部失败")
        
        overall_results.append({
            "config": config,
            "stats": stats if success_results else None,
            "errors": errors
        })
        
        time.sleep(2)  # 测试间隔
    
    # 生成性能报告
    print("\n" + "=" * 60)
    print("📊 性能测试总结")
    print("=" * 60)
    
    for result in overall_results:
        config = result["config"]
        if result["stats"]:
            stats = result["stats"]
            print(f"{config['name']:15} | {stats['success_rate']:5.1f}% | {stats['avg_time']:6.0f}ms | {stats['throughput']:5.1f}/min | {result['errors']}错误")
        else:
            print(f"{config['name']:15} | 全部失败 | {result['errors']}错误")

def stability_test():
    """稳定性测试 - 长时间运行"""
    print("\n🔒 稳定性测试 (长时间运行)")
    print("=" * 60)
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    test_prompts = [
        "写一个简短的问候",
        "解释人工智能",
        "Python的基本语法",
        "机器学习应用",
        "创作一句诗"
    ]
    
    duration_minutes = 2  # 测试时长
    end_time = time.time() + duration_minutes * 60
    request_count = 0
    success_count = 0
    response_times = []
    
    print(f"运行 {duration_minutes} 分钟稳定性测试...")
    
    while time.time() < end_time:
        prompt = test_prompts[request_count % len(test_prompts)]
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0.4,
            "stream": False
        }
        
        start_time = time.time()
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            
            if response.status_code == 200:
                success_count += 1
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)
                
                if request_count % 5 == 0:
                    print(f"   ✅ 请求 {request_count + 1}: {response_time:.0f}ms")
                    
            else:
                print(f"   ❌ 请求 {request_count + 1}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 请求 {request_count + 1}: {e}")
        
        request_count += 1
        time.sleep(0.5)  # 请求间隔
    
    # 稳定性报告
    if response_times:
        avg_time = statistics.mean(response_times)
        success_rate = success_count / request_count * 100
        
        print(f"\n📈 稳定性测试结果:")
        print(f"   总请求: {request_count}")
        print(f"   成功: {success_count} ({success_rate:.1f}%)")
        print(f"   平均响应: {avg_time:.0f}ms")
        print(f"   最长运行: {duration_minutes} 分钟")
    else:
        print("❌ 稳定性测试失败")

if __name__ == "__main__":
    performance_test()
    stability_test()