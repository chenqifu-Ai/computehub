#!/usr/bin/env python3
"""测试语音服务连接"""

import socket
import time

def test_voice_service(host='127.0.0.1', port=9999):
    """测试语音服务"""
    try:
        # 创建socket连接
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        
        print(f"🔗 尝试连接到 {host}:{port}...")
        client.connect((host, port))
        print("✅ 连接成功!")
        
        # 测试命令
        test_commands = ["你好", "时间", "测试"]
        
        for cmd in test_commands:
            print(f"📤 发送: {cmd}")
            client.send(cmd.encode('utf-8'))
            
            # 接收响应
            response = client.recv(1024).decode('utf-8')
            print(f"📥 收到: {response}")
            time.sleep(1)
        
        client.close()
        print("✅ 测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 测试语音服务...")
    success = test_voice_service()
    
    if success:
        print("🎉 语音服务正常工作!")
    else:
        print("⚠️  语音服务需要检查")