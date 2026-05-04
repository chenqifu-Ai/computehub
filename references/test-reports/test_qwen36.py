#!/usr/bin/env python3
"""
测试Qwen 3.6 35B模型连接和响应
"""

import requests
import json
import time

def test_qwen36_model():
    """测试Qwen 3.6 35B模型"""
    
    # API配置
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 测试消息
    test_messages = [
        {"role": "user", "content": "请用中文简单介绍一下你自己，并说明你的主要能力特点。"}
    ]
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": test_messages,
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False
    }
    
    print("🧪 开始测试Qwen 3.6 35B模型...")
    print(f"📡 API地址: {api_url}")
    print(f"🔑 API密钥: {api_key[:10]}...{api_key[-4:]}")
    print("📝 测试问题:", test_messages[0]['content'])
    print("-" * 50)
    
    try:
        start_time = time.time()
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                
                print("✅ 模型测试成功!")
                print(f"⏱️  响应时间: {response_time}ms")
                print(f"📊 Token使用: 输入{usage.get('prompt_tokens', 'N/A')} | 输出{usage.get('completion_tokens', 'N/A')} | 总计{usage.get('total_tokens', 'N/A')}")
                print("\n🤖 模型回复:")
                print("-" * 30)
                print(content)
                print("-" * 30)
                
                return True, content, response_time
            else:
                print("❌ 响应格式异常:", result)
                return False, "响应格式异常", response_time
                
        else:
            print(f"❌ API请求失败: 状态码 {response.status_code}")
            print(f"响应内容: {response.text}")
            return False, f"HTTP {response.status_code}", response_time
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时 (30秒)")
        return False, "请求超时", 30000
        
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误 - 请检查网络连接或API地址")
        return False, "连接错误", 0
        
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False, str(e), 0

if __name__ == "__main__":
    success, response, response_time = test_qwen36_model()
    
    if success:
        print(f"\n🎉 Qwen 3.6 35B模型测试完成!")
        print(f"✅ 状态: 成功")
        print(f"⏱️  响应时间: {response_time}ms")
    else:
        print(f"\n❌ Qwen 3.6 35B模型测试失败!")
        print(f"❌ 错误信息: {response}")