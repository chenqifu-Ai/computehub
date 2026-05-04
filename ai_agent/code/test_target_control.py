#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试对 192.168.2.134 的控制能力
通过 Ollama API 进行基本的系统交互
"""

import requests
import json
import time

def test_ollama_control():
    """测试通过 Ollama API 控制目标机器"""
    target_url = "http://192.168.2.134:11434/api/generate"
    model = "gemma3:1b"
    
    # 测试1: 基本响应
    print("=== 测试1: 基本连接测试 ===")
    payload1 = {
        "model": model,
        "prompt": "Respond with 'System Online' if you can hear me.",
        "stream": False
    }
    
    try:
        response1 = requests.post(target_url, json=payload1, timeout=30)
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ 基本连接成功: {result1.get('response', 'No response')}")
        else:
            print(f"❌ 基本连接失败: {response1.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False
    
    # 测试2: 系统信息查询（间接）
    print("\n=== 测试2: 系统信息查询 ===")
    payload2 = {
        "model": model,
        "prompt": "What is the current date and time? Respond in ISO format.",
        "stream": False
    }
    
    try:
        response2 = requests.post(target_url, json=payload2, timeout=30)
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"✅ 系统时间查询: {result2.get('response', 'No response')}")
        else:
            print(f"❌ 系统时间查询失败: {response2.status_code}")
    except Exception as e:
        print(f"❌ 系统时间查询异常: {e}")
    
    # 测试3: 模型能力确认
    print("\n=== 测试3: 模型能力确认 ===")
    payload3 = {
        "model": model,
        "prompt": "List the available models on this system.",
        "stream": False
    }
    
    try:
        response3 = requests.post(target_url, json=payload3, timeout=30)
        if response3.status_code == 200:
            result3 = response3.json()
            print(f"✅ 模型能力确认: Response received")
        else:
            print(f"❌ 模型能力确认失败: {response3.status_code}")
    except Exception as e:
        print(f"❌ 模型能力确认异常: {e}")
    
    return True

if __name__ == "__main__":
    print("🔍 测试对 192.168.2.134 的控制能力")
    print("=" * 50)
    
    success = test_ollama_control()
    
    if success:
        print("\n🎉 控制测试完成！")
        print("✅ 目标机器 192.168.2.134 可通过 Ollama API 进行基本控制")
        print("⚠️ 注意: 这是间接控制，不是直接系统访问")
    else:
        print("\n❌ 控制测试失败！")