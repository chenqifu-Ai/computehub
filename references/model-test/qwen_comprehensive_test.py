#!/usr/bin/env python3
"""
Qwen 3.6-35B 全面能力测试
测试内容包括：语言理解、代码生成、逻辑推理、知识问答、创意写作
"""

import requests
import json
import time

def test_qwen_comprehensive():
    base_url = "http://58.23.129.98:8001/v1"
    api_key = "78sadn09bjawde123e"
    model = "qwen3.6-35b"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    print("🤖 Qwen 3.6-35B 全面能力测试")
    print("=" * 60)
    print(f"📡 API: {base_url}")
    print(f"🔑 Key: {api_key[:8]}...{api_key[-4:]}")
    print("-" * 60)
    
    # 测试用例
    test_cases = [
        {
            "name": "语言理解",
            "prompt": "请用中文、英文、法文三种语言说'你好，世界！'"
        },
        {
            "name": "代码生成", 
            "prompt": "用Python写一个函数，计算斐波那契数列的第n项"
        },
        {
            "name": "逻辑推理",
            "prompt": "如果所有的猫都会爬树，而Tom是一只猫，那么Tom会爬树吗？请用逻辑推理说明"
        },
        {
            "name": "知识问答",
            "prompt": "请简要介绍人工智能的发展历史"
        },
        {
            "name": "创意写作",
            "prompt": "写一个关于机器人和人类成为朋友的短故事开头（100字以内）"
        }
    ]
    
    total_tests = len(test_cases)
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 测试 {i}/{total_tests}: {test_case['name']}")
        print(f"  问题: {test_case['prompt']}")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": test_case["prompt"]}],
                    "max_tokens": 300,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    reply = result["choices"][0]["message"]["content"]
                    usage = result.get("usage", {})
                    
                    print(f"  ✅ 成功! ({response_time:.0f}ms)")
                    print(f"  回答: {reply[:150]}...")
                    print(f"  📊 Token使用: 输入{usage.get('prompt_tokens', 0)} | 输出{usage.get('completion_tokens', 0)}")
                    
                    passed_tests += 1
                else:
                    print(f"  ❌ 响应格式错误")
            else:
                print(f"  ❌ HTTP错误: {response.status_code}")
                print(f"     错误信息: {response.text[:100]}")
                
        except requests.exceptions.ConnectionError:
            print("  ❌ 连接失败")
            break
        except requests.exceptions.Timeout:
            print("  ❌ 请求超时")
        except Exception as e:
            print(f"  ❌ 异常: {e}")
    
    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print(f"   总测试数: {total_tests}")
    print(f"   通过数: {passed_tests}")
    print(f"   通过率: {passed_tests/total_tests*100:.1f}%")
    
    # 性能评估
    if passed_tests > 0:
        print("\n🎯 模型能力评估:")
        if passed_tests == total_tests:
            print("   ✅ 优秀 - 所有测试项目均通过")
        elif passed_tests >= total_tests * 0.7:
            print("   🟡 良好 - 大部分测试项目通过") 
        else:
            print("   🔴 需改进 - 多个测试项目失败")
    
    print("\n💡 建议:")
    if passed_tests == 0:
        print("   1. 检查API密钥和服务器配置")
        print("   2. 确认服务器是否正常运行")
        print("   3. 检查网络连接")
    else:
        print("   1. 模型基本功能正常")
        print("   2. 可根据具体需求进行深度测试")
        print("   3. 建议测试更多专业领域问题")

if __name__ == "__main__":
    test_qwen_comprehensive()