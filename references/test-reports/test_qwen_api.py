#!/usr/bin/env python3
"""
测试 Qwen 3.6 35B API 连接和响应
"""

import requests
import json
import time

def test_qwen_api():
    # API配置
    base_url = "http://58.23.129.98:8001/v1"
    api_key = "78sadn09bjawde123e"
    model = "qwen3.6-35b"
    
    # 请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 测试消息
    test_messages = [
        {"role": "user", "content": "你好，请简单介绍一下你自己"}
    ]
    
    # 请求数据
    data = {
        "model": model,
        "messages": test_messages,
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": False
    }
    
    print("🔧 开始测试 Qwen 3.6 35B API...")
    print(f"📡 API地址: {base_url}")
    print(f"🤖 模型: {model}")
    print(f"🔑 API密钥: {api_key[:8]}...{api_key[-4:]}")
    print("-" * 50)
    
    try:
        # 测试连接
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        
        print(f"✅ 连接成功! 响应时间: {response_time}ms")
        print(f"📊 状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 提取回复内容
            if "choices" in result and len(result["choices"]) > 0:
                reply = result["choices"][0]["message"]["content"]
                print("🎯 API响应内容:")
                print("-" * 30)
                print(reply)
                print("-" * 30)
                
                # 显示使用情况
                if "usage" in result:
                    usage = result["usage"]
                    print(f"📈 Token使用: 输入{usage.get('prompt_tokens', 0)} | 输出{usage.get('completion_tokens', 0)} | 总计{usage.get('total_tokens', 0)}")
            
            print("\n🎉 API测试成功! Qwen 3.6 35B 正常工作")
            
        else:
            print(f"❌ API返回错误: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 无法连接到API服务器")
        print("请检查网络连接和服务器状态")
        
    except requests.exceptions.Timeout:
        print("❌ 连接超时: API响应时间过长")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        
    except Exception as e:
        print(f"❌ 未知错误: {e}")

if __name__ == "__main__":
    test_qwen_api()