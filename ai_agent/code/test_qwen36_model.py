#!/usr/bin/env python3
"""测试 qwen3.6-35b 模型"""

import urllib.request
import json

BASE_URL = "http://58.23.129.98:8000/v1"
API_KEY = "78sadn09bjawde123e"

def test_model():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 测试 1: 列出模型
    print("=" * 50)
    print("🧪 测试 1: 列出可用模型")
    print("=" * 50)
    
    req = urllib.request.Request(f"{BASE_URL}/v1/models", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            models = data.get("data", [])
            for m in models:
                print(f"  - {m.get('id')}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 测试 2: 发送简单对话
    print("\n" + "=" * 50)
    print("🧪 测试 2: 简单对话测试")
    print("=" * 50)
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [
            {"role": "system", "content": "你是一个简洁的测试助手。"},
            {"role": "user", "content": "你好，请回复'测试成功'并说一句话。"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE_URL}/v1/chat/completions", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            print(f"  回复: {content}")
            print(f"  ✅ 测试成功！")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 测试 3: 复杂推理
    print("\n" + "=" * 50)
    print("🧪 测试 3: 代码生成测试")
    print("=" * 50)
    
    payload2 = {
        "model": "qwen3.6-35b",
        "messages": [
            {"role": "system", "content": "你是一个编程助手。"},
            {"role": "user", "content": "用 Python 写一个快速排序函数"}
        ],
        "max_tokens": 200,
        "temperature": 0.5
    }
    
    data2 = json.dumps(payload2).encode()
    req2 = urllib.request.Request(f"{BASE_URL}/v1/chat/completions", data=data2, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req2, timeout=30) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            print(f"  {content}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 所有测试完成")
    print("=" * 50)

if __name__ == "__main__":
    test_model()
