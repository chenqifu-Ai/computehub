#!/usr/bin/env python3
"""
Qwen 3.6 35B 基础能力测试
测试模型的基本功能和性能
"""

import requests
import json
import time

def basic_test():
    """基础能力测试"""
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    print("🧪 Qwen 3.6 35B 基础能力测试")
    print("=" * 50)
    print(f"API地址: {api_url}")
    print(f"模型: qwen3.6-35b")
    print("=" * 50)
    
    # 测试用例
    test_cases = [
        {
            "name": "基础问答",
            "prompt": "你好，请介绍一下你自己。",
            "max_tokens": 300,
            "temperature": 0.3
        },
        {
            "name": "知识问答", 
            "prompt": "解释一下机器学习和深度学习的区别。",
            "max_tokens": 400,
            "temperature": 0.3
        },
        {
            "name": "逻辑推理",
            "prompt": "如果所有的鸟都会飞，而企鹅是一种鸟，那么企鹅会飞吗？请解释原因。",
            "max_tokens": 200,
            "temperature": 0.2
        },
        {
            "name": "代码生成",
            "prompt": "用Python写一个函数来计算斐波那契数列。",
            "max_tokens": 300,
            "temperature": 0.3
        },
        {
            "name": "创意写作",
            "prompt": "写一首关于人工智能的短诗。",
            "max_tokens": 200,
            "temperature": 0.7
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    total_start = time.time()
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] 🔍 {test['name']}")
        print(f"   📝 {test['prompt']}")
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": test["prompt"]}],
            "max_tokens": test["max_tokens"],
            "temperature": test["temperature"],
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                
                response_time = round((end_time - start_time) * 1000, 2)
                
                print(f"   ✅ 成功 | 时间: {response_time}ms")
                print(f"   🔢 Token使用: 输入{usage.get('prompt_tokens', 0)} / 输出{usage.get('completion_tokens', 0)} / 总计{usage.get('total_tokens', 0)}")
                
                # 显示回答的摘要
                lines = content.split('\n')
                print(f"   💡 回答摘要:")
                for line in lines[:3]:
                    if line.strip():
                        print(f"      {line.strip()}")
                if len(lines) > 3:
                    print(f"      ... (共{len(lines)}行)")
                    
            else:
                print(f"   ❌ 失败: HTTP {response.status_code}")
                print(f"   📄 响应: {response.text[:100]}...")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ 超时: 请求超过30秒")
        except requests.exceptions.ConnectionError:
            print(f"   🔌 连接错误: 无法连接到服务器")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
        
        print("   " + "-" * 40)
        time.sleep(1)  # 避免请求过于频繁
    
    total_time = round(time.time() - total_start, 2)
    print(f"\n🎯 测试完成! 总耗时: {total_time}秒")

def check_api_status():
    """检查API状态"""
    print("🔍 检查API状态...")
    
    api_url = "http://58.23.129.98:8000/v1/models"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            models = response.json()
            print("✅ API状态正常")
            print("📋 可用模型:")
            for model in models.get('data', []):
                print(f"   • {model.get('id')}")
        else:
            print(f"❌ API状态异常: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到API: {e}")

if __name__ == "__main__":
    check_api_status()
    print()
    basic_test()