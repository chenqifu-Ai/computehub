#!/usr/bin/env python3
"""
Qwen 3.6 35B 详细测试
处理API响应中的content为null的情况
"""

import requests
import json
import time

def detailed_test():
    """详细测试Qwen 3.6 35B模型"""
    
    api_url = "http://58.23.129.98:8001/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    model_name = "qwen3.6-35b"
    
    print("🧪 Qwen 3.6 35B 详细测试")
    print("=" * 60)
    print(f"API端点: {api_url}")
    print(f"模型: {model_name}")
    print("=" * 60)
    
    # 测试不同配置
    test_configs = [
        {
            "name": "基础测试",
            "prompt": "Hello, how are you?",
            "max_tokens": 50,
            "temperature": 0.3
        },
        {
            "name": "中文测试",
            "prompt": "你好，请用中文回答",
            "max_tokens": 100,
            "temperature": 0.3
        },
        {
            "name": "长回答测试",
            "prompt": "请详细解释人工智能的发展历史",
            "max_tokens": 300,
            "temperature": 0.5
        },
        {
            "name": "创意测试",
            "prompt": "写一首关于科技的短诗",
            "max_tokens": 150,
            "temperature": 0.8
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n[{i}/{len(test_configs)}] 🔍 {config['name']}")
        print(f"   📝 Prompt: {config['prompt']}")
        print(f"   ⚙️  配置: max_tokens={config['max_tokens']}, temp={config['temperature']}")
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": config["prompt"]}],
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            end_time = time.time()
            
            response_time = round((end_time - start_time) * 1000, 2)
            
            print(f"   ⏱️  响应时间: {response_time}ms")
            print(f"   📡 HTTP状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # 分析响应结构
                print(f"   📊 响应ID: {result.get('id', 'N/A')}")
                
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    
                    # 检查content字段
                    content = choice.get('message', {}).get('content')
                    if content is not None:
                        print(f"   ✅ Content: {content[:100]}...")
                    else:
                        print(f"   ⚠️  Content: null")
                        # 检查其他可能包含内容的字段
                        if 'reasoning' in choice.get('message', {}):
                            reasoning = choice['message']['reasoning']
                            print(f"   💭 Reasoning: {reasoning[:100]}...")
                        
                    # 检查finish_reason
                    finish_reason = choice.get('finish_reason')
                    print(f"   🏁 Finish Reason: {finish_reason}")
                    
                # 显示使用情况
                usage = result.get('usage', {})
                print(f"   🔢 Token使用: 输入{usage.get('prompt_tokens', 0)} / 输出{usage.get('completion_tokens', 0)} / 总计{usage.get('total_tokens', 0)}")
                
                # 显示完整的响应结构（调试用）
                print(f"   🔍 响应结构键: {list(result.keys())}")
                if 'choices' in result:
                    print(f"   🔍 Choice结构: {list(result['choices'][0].keys())}")
                    if 'message' in result['choices'][0]:
                        print(f"   🔍 Message结构: {list(result['choices'][0]['message'].keys())}")
                
            else:
                print(f"   ❌ HTTP错误: {response.status_code}")
                print(f"   📄 错误信息: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
        
        print("   " + "-" * 50)
        time.sleep(2)

def test_with_different_settings():
    """测试不同的参数设置"""
    print("\n🎛️  测试不同参数设置")
    print("=" * 60)
    
    api_url = "http://58.23.129.98:8001/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 测试不同的temperature设置
    temperatures = [0.1, 0.5, 0.9]
    prompt = "写一个简短的创意故事开头"
    
    for temp in temperatures:
        print(f"\n🌡️  Temperature = {temp}")
        print(f"   📝 Prompt: {prompt}")
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": temp,
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message'].get('content')
                reasoning = result['choices'][0]['message'].get('reasoning', '')
                
                response_time = round((end_time - start_time) * 1000, 2)
                
                print(f"   ⏱️  响应时间: {response_time}ms")
                
                if content:
                    print(f"   📝 Content: {content[:80]}...")
                elif reasoning:
                    print(f"   💭 Reasoning: {reasoning[:80]}...")
                else:
                    print(f"   ⚠️  无内容输出")
                    
            else:
                print(f"   ❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
        
        time.sleep(1)

def check_model_capabilities():
    """检查模型能力"""
    print("\n🔧 检查模型能力")
    print("=" * 60)
    
    api_url = "http://58.23.129.98:8001/v1/models"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ 模型信息:")
            for model in data.get('data', []):
                print(f"   • 模型ID: {model.get('id')}")
                print(f"   • 对象类型: {model.get('object')}")
                print(f"   • 创建时间: {model.get('created')}")
                
                if 'permission' in model:
                    perm = model['permission']
                    print(f"   • 权限: {perm.get('id')}")
                    print(f"   • 允许采样: {perm.get('allow_sampling')}")
                    print(f"   • 允许日志概率: {perm.get('allow_logprobs')}")
                    print(f"   • 允许微调: {perm.get('allow_fine_tuning')}")
                
                print("   " + "-" * 30)
        else:
            print(f"❌ 无法获取模型信息: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    check_model_capabilities()
    detailed_test()
    test_with_different_settings()