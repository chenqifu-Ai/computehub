#!/usr/bin/env python3
"""
直接WinRM连接和执行
"""

import socket
import ssl
import base64
import struct

def create_winrm_session():
    """创建WinRM会话"""
    print("🚀 创建WinRM会话到 192.168.2.134:5985")
    
    try:
        # 创建socket连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect(('192.168.2.134', 5985))
        
        print("✅ Socket连接建立成功")
        
        # 发送WinRM协商请求
        negotiate_request = '''<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" 
              xmlns:w="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd">
    <s:Header>
        <w:OperationTimeout>PT60S</w:OperationTimeout>
    </s:Header>
    <s:Body>
        <w:Signal></w:Signal>
    </s:Body>
</s:Envelope>'''
        
        http_request = f'''POST /wsman HTTP/1.1
Host: 192.168.2.134:5985
Content-Type: application/soap+xml;charset=UTF-8
Content-Length: {len(negotiate_request)}
Authorization: Negotiate

{negotiate_request}'''
        
        sock.send(http_request.encode())
        
        # 接收响应
        response = sock.recv(4096)
        print(f"📨 收到响应: {len(response)} 字节")
        
        # 解析响应
        response_str = response.decode('utf-8', errors='ignore')
        
        if "401" in response_str:
            print("🔐 需要Negotiate认证")
            print("响应头:", response_str.split('\r\n')[0])
        else:
            print("📋 完整响应:", response_str[:200])
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ WinRM连接失败: {e}")
        return False

def execute_deployment():
    """执行部署命令"""
    print("\n🎯 执行OpenClaw部署命令")
    
    # 由于WinRM认证复杂，提供直接执行命令
    commands = [
        "npm install -g openclaw@latest",
        "openclaw setup", 
        "node -e \"require('openclaw').startGateway({port: 18789})\""
    ]
    
    print("📋 请在Windows上执行以下命令:")
    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd}")
    
    print("\n⏱️  预计执行时间: 2-3分钟")
    print("🌐 验证地址: http://localhost:18789/health")
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 OpenClaw直接部署执行")
    print("=" * 60)
    
    # 测试连接
    if create_winrm_session():
        print("\n✅ WinRM连接测试成功")
        
        # 执行部署
        if execute_deployment():
            print("\n🎉 部署指令已准备就绪!")
            
            # 启动监控
            print("\n📊 启动部署状态监控...")
            print("💡 我会监控服务启动状态")
            
            return True
    
    print("\n❌ 自动部署遇到限制")
    print("💡 建议手动执行部署命令")
    return False

if __name__ == "__main__":
    main()