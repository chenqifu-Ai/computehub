#!/usr/bin/env python3
"""
Ollama云端模型测试脚本
测试所有模型的可用性和响应时间
"""

import requests
import json
import time
from datetime import datetime
import sys

# Ollama云端API配置
OLLAMA_CLOUD_API = "https://ollama.com/api"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

# 测试提示词
TEST_PROMPT = "你好，请用一句话介绍你自己。"

# 模型列表（从API获取）
MODELS = [
    "glm-4.7", "qwen3-next:80b", "gpt-oss:120b", "ministral-3:3b", "gemma3:27b",
    "nemotron-3-super", "nemotron-3-nano:30b", "qwen3-vl:235b-instruct", "minimax-m2.5",
    "cogito-2.1:671b", "glm-4.6", "devstral-2:123b", "gemma3:12b", "glm-5",
    "glm-5.1", "kimi-k2.5", "qwen3-coder:480b", "minimax-m2.1", "minimax-m2.7",
    "ministral-3:14b", "mistral-large-3:675b", "minimax-m2", "gemma4:31b",
    "rnj-1:8b", "qwen3.5:397b", "kimi-k2-thinking", "qwen3-coder-next",
    "qwen3-vl:235b", "devstral-small-2:24b", "gemini-3-flash-preview", "gemma3:4b",
    "kimi-k2:1t", "deepseek-v3.2", "ministral-3:8b", "deepseek-v3.1:671b", "gpt-oss:20b"
]

def test_model(model_name):
    """测试单个模型的可用性"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "prompt": TEST_PROMPT,
        "stream": False
    }
    
    start_time = time.time()
    result = {
        "model": model_name,
        "status": "unknown",
        "response_time": 0,
        "error": None,
        "response": None
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_CLOUD_API}/generate",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response_time = time.time() - start_time
        result["response_time"] = round(response_time, 2)
        
        if response.status_code == 200:
            data = response.json()
            result["status"] = "✅ 可用"
            result["response"] = data.get("response", "")[:100]  # 只保存前100字符
        else:
            result["status"] = f"❌ 错误 ({response.status_code})"
            result["error"] = response.text[:200]
            
    except requests.exceptions.Timeout:
        result["status"] = "⏱️ 超时"
        result["error"] = "请求超时（30秒）"
        result["response_time"] = 30.0
        
    except requests.exceptions.RequestException as e:
        result["status"] = "❌ 连接失败"
        result["error"] = str(e)[:200]
        
    except Exception as e:
        result["status"] = "❌ 异常"
        result["error"] = str(e)[:200]
    
    return result

def main():
    """主测试函数"""
    print("=" * 80)
    print("🚀 Ollama云端模型测试")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 待测试模型数: {len(MODELS)}")
    print("=" * 80)
    print()
    
    results = []
    success_count = 0
    fail_count = 0
    
    for i, model in enumerate(MODELS, 1):
        print(f"[{i}/{len(MODELS)}] 测试 {model}...", end=" ", flush=True)
        
        result = test_model(model)
        results.append(result)
        
        if result["status"].startswith("✅"):
            success_count += 1
            print(f"{result['status']} - {result['response_time']}s")
        else:
            fail_count += 1
            print(f"{result['status']}")
        
        # 避免请求过快
        time.sleep(0.5)
    
    # 生成报告
    print()
    print("=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    print(f"✅ 可用模型: {success_count}/{len(MODELS)}")
    print(f"❌ 不可用模型: {fail_count}/{len(MODELS)}")
    print()
    
    # 按状态分类
    available = [r for r in results if r["status"].startswith("✅")]
    unavailable = [r for r in results if not r["status"].startswith("✅")]
    
    if available:
        print("✅ 可用模型列表:")
        print("-" * 80)
        for r in sorted(available, key=lambda x: x["response_time"]):
            print(f"  {r['model']:30s} | {r['response_time']:6.2f}s | {r['response']}")
        print()
    
    if unavailable:
        print("❌ 不可用模型列表:")
        print("-" * 80)
        for r in unavailable:
            print(f"  {r['model']:30s} | {r['status']:20s} | {r['error'] or ''}")
        print()
    
    # 保存结果到文件
    result_file = "/root/.openclaw/workspace/ai_agent/results/ollama_cloud_models_test.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "total_models": len(MODELS),
            "available_count": success_count,
            "unavailable_count": fail_count,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"📁 详细结果已保存到: {result_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()