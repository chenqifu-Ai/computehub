#!/usr/bin/env python3
"""
HTTP基础的WinRM测试
"""

import requests

def test_basic_winrm():
    """基础WinRM测试"""
    print("🔍 基础WinRM连接测试...")
    
    url = "http://192.168.2.134:5985/wsman"
    
    # 简单的HTTP请求测试
    try:
        response = requests.post(
            url,
            data="",
            headers={'Content-Type': 'application/soap+xml'},
            timeout=10
        )
        
        print(f"✅ HTTP响应: {response.status_code}")
        print(f"服务器: {response.headers.get('Server', 'Unknown')}")
        print(f"允许的方法: {response.headers.get('Allow', 'Unknown')}")
        
        if response.status_code == 401:
            print("🔐 需要身份验证 - WinRM服务正常")
            print("支持的认证方式:", response.headers.get('WWW-Authenticate', 'Unknown'))
        elif response.status_code == 200:
            print("🎉 连接成功!")
        else:
            print(f"ℹ️  其他状态: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接被拒绝 - 检查WinRM服务状态")
    except requests.exceptions.Timeout:
        print("⏰ 连接超时 - 检查网络连通性")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    test_basic_winrm()