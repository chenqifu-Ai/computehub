#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 58.23.129.98:8001 服务器性能
"""
import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "http://58.23.129.98:8001/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

def test_latency():
    """测试延迟"""
    print("\n🔴 测试延迟...")
    payloads = [
        {"model": "qwen3.6-35b", "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}], "max_tokens": 10},
        {"model": "qwen3.6-35b", "messages": [{"role": "user", "content": [{"type": "text", "text": "请介绍一下你自己"}]}], "max_tokens": 100},
    ]
    
    for i, payload in enumerate(payloads, 1):
        start = time.time()
        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            elapsed = time.time() - start
            if r.status_code == 200:
                data = r.json()
                tokens = data.get('usage', {}).get('total_tokens', '?')
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"  ✅ 测试 {i}: {elapsed:.2f}s | {tokens} tokens | {content[:50]}")
            else:
                print(f"  ❌ 测试 {i}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  ❌ 测试 {i}: {e}")

def test_concurrency():
    """并发测试"""
    print("\n🔴 并发测试...")
    
    def make_request(i):
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": f"测试并发{i}，请回复：并发测试{i}"}]}],
            "max_tokens": 50
        }
        start = time.time()
        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
            elapsed = time.time() - start
            if r.status_code == 200:
                data = r.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return {'index': i, 'success': True, 'elapsed': elapsed, 'content': content}
            else:
                return {'index': i, 'success': False, 'error': f'HTTP {r.status_code}'}
        except Exception as e:
            return {'index': i, 'success': False, 'error': str(e)}
    
    for n in [1, 5, 10]:
        start = time.time()
        with ThreadPoolExecutor(max_workers=n) as executor:
            futures = [executor.submit(make_request, i) for i in range(1, n+1)]
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except:
                    pass
        
        elapsed = time.time() - start
        success = sum(1 for r in results if r.get('success'))
        avg = sum(r['elapsed'] for r in results if r.get('success')) / success if success > 0 else 0
        print(f"  并发{n}: 总耗时{elapsed:.2f}s | 成功{success}/{n} | 平均{avg:.2f}s")

def test_gpu_info():
    """尝试获取 GPU 信息"""
    print("\n🔴 尝试获取 GPU 信息...")
    
    # 尝试通过 API 获取
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "请告诉我你运行的硬件环境（CPU/GPU/内存/显存等）"}]}],
        "max_tokens": 500
    }
    
    start = time.time()
    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            reasoning = data.get('choices', [{}])[0].get('message', {}).get('reasoning', '')
            print(f"  ✅ 耗时{elapsed:.2f}s")
            print(f"  📝 回答：\n{content[:2000]}")
        else:
            print(f"  ❌ HTTP {r.status_code}")
    except Exception as e:
        print(f"  ❌ {e}")

def test_token_usage():
    """测试 Token 使用量"""
    print("\n🔴 测试 Token 使用情况...")
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "请写一首关于春天的诗"}]}],
        "max_tokens": 200
    }
    
    start = time.time()
    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            tokens = data.get('usage', {}).get('total_tokens', '?')
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"  ✅ 耗时{elapsed:.2f}s | 总 tokens:{tokens}")
            print(f"  📝 诗歌：\n{content[:500]}")
        else:
            print(f"  ❌ HTTP {r.status_code}")
    except Exception as e:
        print(f"  ❌ {e}")

def main():
    print("=" * 80)
    print("  🧪 测试 58.23.129.98:8001 服务器性能")
    print("=" * 80)
    
    test_latency()
    test_concurrency()
    test_gpu_info()
    test_token_usage()
    
    print("\n" + "=" * 80)
    print("  测试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
