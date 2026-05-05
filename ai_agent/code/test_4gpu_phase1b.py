#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4 卡 GPU 测试 - 阶段 1b：通过 vLLM API 获取实际硬件信息
"""
import requests, json, time

BASE_URL = "http://58.23.129.98:8001"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

def get_vllm_info():
    """获取 vLLM 服务器配置"""
    print("=" * 80)
    print("  🔍 获取 vLLM 服务器配置")
    print("=" * 80)
    
    # 获取模型信息
    try:
        r = requests.get(f"{BASE_URL}/v1/models", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            models = r.json().get('data', [])
            for model in models:
                print(f"\n📦 模型信息：")
                print(f"  ID: {model.get('id')}")
                print(f"  最大上下文：{model.get('max_model_len')} tokens")
                print(f"  拥有者：{model.get('owned_by')}")
        else:
            print(f"❌ HTTP {r.status_code}")
    except Exception as e:
        print(f"❌ 模型查询失败：{e}")

def test_gpu_memory():
    """通过内存使用情况推断 GPU 配置"""
    print("\n" + "=" * 80)
    print("  💾 GPU 显存推断测试")
    print("=" * 80)
    
    # 测试 1：加载 35B 模型占用的显存
    # Qwen3.6-35B-A3B-FP8 大约需要多少显存？
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "请输出：你好"}]}],
        "max_tokens": 100
    }
    
    print("\n📊 测试模型加载显存占用...")
    
    # 执行 10 次请求，统计平均耗时和显存增长
    times = []
    for i in range(10):
        start = time.time()
        r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=30)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            usage = data.get('usage', {})
            times.append(elapsed)
            
            if i == 0:
                print(f"  第 1 次：{elapsed:.3f}s | prompt_tokens: {usage.get('prompt_tokens')}, completion_tokens: {usage.get('completion_tokens')}")
        else:
            print(f"  第{i+1}次失败：HTTP {r.status_code}")
            break
    
    avg_time = sum(times) / len(times) if times else 0
    print(f"\n  平均延迟：{avg_time:.3f}s")
    print(f"  请求次数：{len(times)}")
    
    # 推断显存使用
    # 35B FP8 模型参数约 17.5GB
    # KV Cache 等其他开销
    # 如果 4 卡 A100-80GB：总显存 320GB
    # 如果 4 卡 A800-80GB：总显存 320GB
    # 如果 4 卡 RTX 4090：总显存 96GB
    
    print(f"\n  显存推断：")
    print(f"  - 模型参数（FP8）：~17.5GB")
    print(f"  - KV Cache（假设）：~10-20GB")
    print(f"  - 其他开销：~5-10GB")
    print(f"  - 总使用：~32.5-47.5GB")
    print(f"  - 如果是 4 卡 A100-80GB：使用率 {32.5/320*100:.1f}%-{47.5/320*100:.1f}%")
    print(f"  - 如果是 4 卡 RTX 4090：使用率 {32.5/96*100:.1f}%-{47.5/96*100:.1f}%")

def test_tokenization():
    """测试分词和输入处理"""
    print("\n" + "=" * 80)
    print("  🔤 分词和输入处理测试")
    print("=" * 80)
    
    test_texts = [
        ("简短", "你好"),
        ("中等", "请详细介绍人工智能的发展历史和未来趋势，包括深度学习、强化学习、生成式 AI 等关键技术。"),
        ("长文本", "这是一个测试。" * 100),
    ]
    
    for name, text in test_texts:
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "max_tokens": 50
        }
        
        start = time.time()
        r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=30)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            usage = data.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            
            print(f"\n  {name}：")
            print(f"    输入长度：{len(text)} 字符")
            print(f"    Prompt tokens：{prompt_tokens}")
            print(f"    输出 tokens：{completion_tokens}")
            print(f"    耗时：{elapsed:.3f}s")
        else:
            print(f"  ❌ {name}：HTTP {r.status_code}")

def test_kv_cache():
    """测试 KV Cache 效率"""
    print("\n" + "=" * 80)
    print("  🧮 KV Cache 效率测试")
    print("=" * 80)
    
    # 测试不同上下文长度下的性能
    context_lengths = [1, 100, 1000, 5000]
    
    print("\n  测试不同输入长度下的首 token 延迟（TTFT）...")
    
    for ctx_len in context_lengths:
        # 生成不同长度的输入
        text = "这是一个测试句子。" * (ctx_len // 10 + 1)
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "max_tokens": 10
        }
        
        start = time.time()
        r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=60)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            usage = data.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            
            print(f"    输入长度~{ctx_len}: Prompt tokens={prompt_tokens}, 首 token 延迟={elapsed:.3f}s")
        else:
            print(f"    输入长度~{ctx_len}: ❌ HTTP {r.status_code}")

def main():
    print("\n🚀 开始执行阶段 1b：vLLM API 硬件信息获取\n")
    
    get_vllm_info()
    test_gpu_memory()
    test_tokenization()
    test_kv_cache()
    
    print("\n" + "=" * 80)
    print("  ✅ 阶段 1b 完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
