#!/usr/bin/env python3
"""
简单WinRM协议测试
"""

import requests
from requests_ntlm import HttpNtlmAuth
import xml.etree.ElementTree as ET

def test_winrm():
    """测试WinRM连接"""
    print("🔍 测试WinRM连接...")
    
    # WinRM端点
    url = "http://192.168.2.134:5985/wsman"
    
    # 基本的WinRM SOAP请求
    soap_request = '''
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" 
              xmlns:w="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd">
    <s:Header>
        <w:OperationTimeout>PT60S</w:OperationTimeout>
    </s:Header>
    <s:Body>
        <w:Signal></w:Signal>
    </s:Body>
</s:Envelope>
'''
    
    try:
        # 发送WinRM请求
        response = requests.post(
            url,
            data=soap_request,
            headers={
                'Content-Type': 'application/soap+xml;charset=UTF-8',
                'User-Agent': 'OpenClaw-WinRM-Client'
            },
            auth=HttpNtlmAuth('administrator', 'c9fc9f,.'),
            timeout=10
        )
        
        print(f"✅ WinRM响应: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("🎉 WinRM认证成功!")
            # 尝试解析SOAP响应
            try:
                root = ET.fromstring(response.text)
                print("SOAP响应解析成功")
            except:
                print("SOAP响应内容:", response.text[:200])
        else:
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 检查网络和防火墙")
    except requests.exceptions.Timeout:
        print("⏰ 请求超时")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

if __name__ == "__main__":
    test_winrm()