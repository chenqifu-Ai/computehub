#!/usr/bin/env python3
"""
测试 Qwen 3.6 35B API - 多种认证方式测试
"""

import requests
import json

def test_different_auth_methods():
    base_url = "http://58.23.129.98:8001/v1"
    api_key = "78sadn09bjawde123e"
    model = "qwen3.6-35b"
    
    # 测试不同的认证方式
    auth_methods = [
        {
            "name": "Bearer Token",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        },
        {
            "name": "API-Key Header",
            "headers": {
                "Content-Type": "application/json",
                "API-Key": api_key
            }
        },
        {
            "name": "X-API-Key Header",
            "headers": {
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
        },
        {
            "name": "Query Parameter",
            "headers": {"Content-Type": "application/json"},
            "params": {"api_key": api_key}
        }
    ]
    
    # 测试消息
    messages = [{"role": "user", "content": "你好"}]
    data = {"model": model, "messages": messages, "max_tokens": 50}
    
    print("🔧 测试不同的API认证方式...")
    print(f"📡 目标: {base_url}")
    print("-" * 50)
    
    for method in auth_methods:
        print(f"\n🔍 测试方式: {method['name']}")
        
        try:
            # 准备请求参数
            request_kwargs = {
                "url": f"{base_url}/chat/completions",
                "json": data,
                "timeout": 10,
                "headers": method.get("headers", {})
            }
            
            if "params" in method:
                request_kwargs["params"] = method["params"]
            
            response = requests.post(**request_kwargs)
            
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ 成功! 响应: {result.get('choices', [{}])[0].get('message', {}).get('content', '')[:50]}...")
                break
            elif response.status_code == 401:
                print(f"  ❌ 认证失败")
            else:
                print(f"  ⚠️  其他错误: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
    
    print("\n" + "="*50)
    print("如果所有认证方式都失败，请检查:")
    print("1. API密钥是否正确")
    print("2. 服务器是否要求其他认证方式")
    print("3. 服务器文档中的认证要求")

if __name__ == "__main__":
    test_different_auth_methods()