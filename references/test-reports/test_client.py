#!/usr/bin/env python3
"""
测试客户端
用于测试语音服务器
"""

import socket
import time

def test_server():
    """测试服务器"""
    print("🔧 测试语音服务器")
    print("💡 模拟手机连接")
    print("="*40)
    
    try:
        # 连接服务器
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 8888))
        print("✅ 连接服务器成功")
        
        # 测试命令
        test_commands = ['你好', '时间', '测试', '无效命令', '退出']
        
        for cmd in test_commands:
            print(f"\n📨 发送: {cmd}")
            client.send(cmd.encode('utf-8'))
            
            # 接收响应
            response = client.recv(1024).decode('utf-8')
            print(f"📤 收到: {response}")
            
            time.sleep(1)
        
        client.close()
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    print("🔧 语音服务器测试工具")
    print("💡 用于验证基础功能")
    print("="*50)
    
    print("\n📋 测试步骤:")
    print("1. 先运行服务器: python3 voice_server.py")
    print("2. 然后运行测试: python3 test_client.py")
    print("3. 观察通信结果")
    
    print("\n🚀 实际使用:")
    print("• 手机使用网络调试助手")
    print("• 连接到电脑IP:8888")
    print("• 发送文本命令")
    print("• 接收语音响应")
    
    print("\n" + "="*50)
    print("✅ 测试工具就绪")

if __name__ == "__main__":
    main()