#!/usr/bin/env python3
"""
基础连接测试 - 检查服务器是否在线和可访问
"""

import requests

def test_basic_connection():
    base_url = "http://58.23.129.98:8001"
    
    print("🔧 基础连接测试...")
    print(f"📡 目标服务器: {base_url}")
    print("-" * 40)
    
    # 测试1: 基础HTTP连接
    try:
        response = requests.get(base_url, timeout=10)
        print(f"✅ HTTP连接成功 - 状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
    except Exception as e:
        print(f"❌ HTTP连接失败: {e}")
        return
    
    # 测试2: 检查/v1端点
    try:
        response = requests.get(f"{base_url}/v1", timeout=10)
        print(f"📊 /v1端点 - 状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应内容: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ /v1端点访问失败: {e}")
    
    # 测试3: 检查/models端点
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=10)
        print(f"🤖 /models端点 - 状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   可用模型: {response.text}")
        elif response.status_code == 401:
            print("   ⚠️  需要认证才能访问模型列表")
    except Exception as e:
        print(f"❌ /models端点访问失败: {e}")
    
    print("\n" + "="*40)
    print("建议下一步:")
    print("1. 确认API密钥是否正确")
    print("2. 检查服务器文档中的认证要求")
    print("3. 确认服务器是否配置了正确的CORS或认证中间件")

if __name__ == "__main__":
    test_basic_connection()