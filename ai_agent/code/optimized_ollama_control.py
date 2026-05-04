#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的 Ollama 控制脚本 - 针对 192.168.2.134
使用更短、更直接的提示词避免超时
"""

import requests
import json
import time

def optimized_ollama_control():
    """优化的 Ollama 控制测试"""
    target_url = "http://192.168.2.134:11434/api/generate"
    model = "gemma3:1b"
    
    # 测试序列 - 简短直接的提示
    test_prompts = [
        ("系统确认", "OK?"),
        ("时间", "Time?"),
        ("主机名", "Hostname?"),
        ("用户", "User?"),
        ("目录", "Dir C:?"),
        ("进程", "Processes?")
    ]
    
    successful_tests = []
    
    for test_name, prompt in test_prompts:
        print(f"\n=== {test_name} 测试 ===")
        print(f"提示: '{prompt}'")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 50,  # 限制输出长度
                "temperature": 0.1   # 降低随机性
            }
        }
        
        try:
            response = requests.post(target_url, json=payload, timeout=15)
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                print(f"✅ 响应: {response_text[:100]}...")
                successful_tests.append(test_name)
            else:
                print(f"❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 超时或错误: {e}")
        
        # 短暂延迟避免过载
        time.sleep(2)
    
    print(f"\n🎯 成功测试: {len(successful_tests)}/{len(test_prompts)}")
    print(f"成功项目: {successful_tests}")
    
    return len(successful_tests) > 0

if __name__ == "__main__":
    print("⚡ 优化 Ollama 控制测试")
    print("=" * 40)
    
    success = optimized_ollama_control()
    
    if success:
        print("\n✅ 优化控制测试成功！")
        print("现在可以进行更可靠的交互控制")
    else:
        print("\n❌ 优化控制测试失败")
        print("可能需要其他控制方法")