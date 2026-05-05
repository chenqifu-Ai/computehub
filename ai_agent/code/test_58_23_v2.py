#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 58.23.129.98:8001 服务器性能 - 完整版
"""
import requests, json, time

API_URL = "http://58.23.129.98:8001/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

def test_latency():
    """测试延迟"""
    print("\n🔴 测试延迟...")
    
    # 测试 1：简单问候
    payload1 = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        "max_tokens": 10
    }
    start = time.time()
    r = requests.post(API_URL, json=payload1, headers=HEADERS, timeout=30)
    elapsed = time.time() - start
    if r.status_code == 200:
        data = r.json()
        print(f"  响应状态码：{r.status_code}")
        print(f"  耗时：{elapsed:.2f}s")
        print(f"  完整响应：{json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
    else:
        print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")

def test_gpu():
    """获取 GPU 信息"""
    print("\n🔴 获取 GPU 信息...")
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "请告诉我你的硬件配置（CPU/GPU/内存/显存）"}]}],
        "max_tokens": 500
    }
    
    start = time.time()
    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
    elapsed = time.time() - start
    
    if r.status_code == 200:
        data = r.json()
        choice = data.get('choices', [{}])[0]
        message = choice.get('message', {})
        content = message.get('content', '')
        reasoning = message.get('reasoning', '')
        
        print(f"  ✅ 耗时：{elapsed:.2f}s")
        print(f"  content 字段：{content[:200] if content else 'NULL'}")
        print(f"  reasoning 字段长度：{len(reasoning) if reasoning else 0}")
        if reasoning:
            print(f"  reasoning 内容：\n{reasoning[:1000]}")
    else:
        print(f"  ❌ HTTP {r.status_code}")

def test_concurrency():
    """并发测试"""
    print("\n🔴 并发测试...")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def make_request(i):
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": f"测试{i}，请回复：并发测试{i}"}]}],
            "max_tokens": 50
        }
        start = time.time()
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            choice = data.get('choices', [{}])[0]
            message = choice.get('message', {})
            content = message.get('content', '')
            reasoning = message.get('reasoning', '')
            tokens = data.get('usage', {}).get('total_tokens', '?')
            return {'index': i, 'success': True, 'elapsed': elapsed, 'tokens': tokens, 'content': (content or reasoning)[:100]}
        else:
            return {'index': i, 'success': False, 'error': f'HTTP {r.status_code}'}
    
    for n in [1, 5, 10, 20]:
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

def main():
    print("=" * 80)
    print("  🧪 测试 58.23.129.98:8001 服务器性能")
    print("=" * 80)
    
    test_latency()
    test_gpu()
    test_concurrency()
    
    print("\n" + "=" * 80)
    print("  测试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
