#!/usr/bin/env python3
"""代理模型全面测试"""

import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置
PROXY_URL = "http://127.0.0.1:8765/v1/chat/completions"
CLOUD_URL = "https://ai.zhangtuokeji.top:9090/v1/chat/completions"
CLOUD_KEY = "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"

MODEL = "qwen3.6-35b"

def send_request(url, prompt, model=MODEL, max_tokens=100, api_key=None, timeout=60):
    """发送请求"""
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }
    
    start = time.time()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        elapsed = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content", "") or msg.get("reasoning", "")
            usage = data.get("usage", {})
            return {
                "success": True,
                "elapsed": elapsed,
                "content": content,
                "content_length": len(content),
                "usage": usage
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {resp.status_code}",
                "elapsed": elapsed
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed": time.time() - start
        }

def test_functionality(name, prompt, max_tokens=100, timeout=60):
    """功能测试"""
    r = send_request(PROXY_URL, prompt, max_tokens=max_tokens, timeout=timeout)
    status = "✅" if r["success"] else "❌"
    print(f"  {status} {name:10s} | {r['elapsed']:.1f}s | {r.get('content_length', 0)} 字", end="")
    if not r["success"]:
        print(f" | {r['error']}")
    else:
        print()
    return r["success"]

def test_performance(url, name, times=5, prompt="测试性能"):
    """性能测试"""
    results = []
    for i in range(times):
        r = send_request(url, prompt, max_tokens=100)
        results.append(r)
    
    if all(r["success"] for r in results):
        times_list = [r["elapsed"] for r in results]
        avg = sum(times_list) / len(times_list)
        print(f"  ✅ {name:15s} | 平均:{avg:.2f}s | 最快:{min(times_list):.2f}s | 最慢:{max(times_list):.2f}s")
        return True
    else:
        print(f"  ❌ {name:15s} | 失败次数: {sum(1 for r in results if not r['success'])}")
        return False

def test_concurrent(url, name, concurrent=5):
    """并发测试"""
    prompts = [f"测试并发 {i}" for i in range(concurrent)]
    results = []
    
    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [executor.submit(send_request, url, p, max_tokens=50) for p in prompts]
        for f in as_completed(futures):
            results.append(f.result())
    
    success_count = sum(1 for r in results if r["success"])
    if success_count == concurrent:
        times = [r["elapsed"] for r in results]
        avg = sum(times) / len(times)
        print(f"  ✅ {name:15s} | {success_count}/{concurrent} | 平均:{avg:.2f}s | 总耗时:{sum(times):.2f}s")
        return True
    else:
        print(f"  ❌ {name:15s} | {success_count}/{concurrent} 成功")
        return False

def compare_models():
    """对比测试"""
    test_prompts = [
        ("简单问答", "你好", 100),
        ("数学计算", "12345 × 67890 = ?", 50),
        ("代码生成", "写一个快速排序 Python 函数", 300),
        ("翻译", "将'你好世界'翻译成英语", 100),
    ]
    
    print("\n  === 对比测试 ===")
    
    for name, prompt, max_tokens in test_prompts:
        r_proxy = send_request(PROXY_URL, prompt, max_tokens=max_tokens)
        r_cloud = send_request(CLOUD_URL, prompt, max_tokens=max_tokens, api_key=CLOUD_KEY)
        
        print(f"\n  【{name}】")
        print(f"    代理 : {r_proxy['elapsed']:.2f}s | {r_proxy.get('content_length', 0)} 字 | {'✅' if r_proxy['success'] else '❌'}")
        print(f"    云端 : {r_cloud['elapsed']:.2f}s | {r_cloud.get('content_length', 0)} 字 | {'✅' if r_cloud['success'] else '❌'}")

def main():
    print("=" * 70)
    print("🧪 代理模型全面测试")
    print("=" * 70)
    
    # 1. 健康检查
    print("\n【1】健康检查")
    print("-" * 70)
    try:
        r = requests.get("http://127.0.0.1:8765/health", timeout=5)
        if r.status_code == 200:
            d = r.json()
            print(f"  ✅ /health: {d['status']}")
            print(f"  ✅ 后端: {d.get('target', 'unknown')}")
        else:
            print(f"  ❌ /health: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ❌ /health: {e}")
    
    # 2. 模型列表
    print("\n【2】模型列表")
    print("-" * 70)
    try:
        r = requests.get("http://127.0.0.1:8765/v1/models", timeout=5)
        if r.status_code == 200:
            models = r.json().get("data", [])
            print(f"  ✅ {len(models)} 个模型可用:")
            for m in models:
                print(f"    - {m['id']}")
        else:
            print(f"  ❌ HTTP {r.status_code}")
    except Exception as e:
        print(f"  ❌ {e}")
    
    # 3. 功能测试
    print("\n【3】功能测试")
    print("-" * 70)
    
    tests = [
        ("简单问答", "你好，请简单介绍一下自己", 100),
        ("数学计算", "12345 × 67890 = ?", 50),
        ("代码生成", "写一个快速排序 Python 函数", 300),
        ("角色扮演", "你是一只傲娇猫，说一句话", 200),
        ("翻译", "将'你好世界'翻译成日语", 100),
        ("逻辑推理", "三门问题：该不该换门？", 300),
        ("知识问答", "量子纠缠是什么？", 200),
        ("总结摘要", "请总结人工智能的主要发展趋势", 300),
    ]
    
    passed = 0
    for name, prompt, max_tokens in tests:
        if test_functionality(name, prompt, max_tokens):
            passed += 1
    print(f"\n  通过: {passed}/{len(tests)}")
    
    # 4. 性能测试（5 次平均）
    print("\n【4】性能测试（5 次平均）")
    print("-" * 70)
    
    performance_tests = [
        ("简单问答", "你好"),
        ("中等问答", "请解释量子计算的基本原理"),
        ("代码生成", "写一个快速排序 Python 函数"),
    ]
    
    for name, prompt in performance_tests:
        test_performance(PROXY_URL, name, prompt=prompt)
    
    # 5. 并发测试
    print("\n【5】并发测试")
    print("-" * 70)
    
    test_concurrent(PROXY_URL, "5 并发")
    
    # 6. 与云端对比
    print("\n【6】与云端对比测试")
    print("-" * 70)
    compare_models()
    
    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
