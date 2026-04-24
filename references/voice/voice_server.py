#!/usr/bin/env python3
"""
语音交互服务器
直接干活，不废话
"""

import socket
import threading
import time

class VoiceServer:
    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.clients = []
        
    def handle_client(self, client_socket, address):
        """处理客户端连接"""
        print(f"🔗 客户端连接: {address}")
        self.clients.append(client_socket)
        
        try:
            while True:
                # 接收数据
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                print(f"📨 收到: {data}")
                
                # 简单的命令处理
                response = self.process_command(data)
                
                # 发送响应
                client_socket.send(response.encode('utf-8'))
                print(f"📤 发送: {response}")
                
        except Exception as e:
            print(f"❌ 客户端错误: {e}")
        finally:
            client_socket.close()
            self.clients.remove(client_socket)
            print(f"🔌 客户端断开: {address}")
    
    def process_command(self, command):
        """处理语音命令"""
        command = command.strip().lower()
        
        # 简单命令映射
        responses = {
            '你好': '你好！我是小智',
            '时间': f'现在时间 {time.strftime("%H:%M")}',
            '日期': f'今天 {time.strftime("%Y年%m月%d日")}',
            '测试': '语音测试成功',
            '退出': '好的，再见'
        }
        
        return responses.get(command, '未知命令，请说: 你好, 时间, 日期, 测试, 退出')
    
    def start(self):
        """启动服务器"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)
        
        print(f"🚀 语音服务器启动在 {self.host}:{self.port}")
        print("💡 等待手机连接...")
        print("🔧 手机可以使用网络调试助手连接")
        
        try:
            while True:
                client_socket, address = server.accept()
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\n👋 服务器关闭")
        finally:
            server.close()

def main():
    print("🔧 创建语音交互服务器")
    print("💡 直接干活，不废话")
    print("="*50)
    
    server = VoiceServer()
    server.start()

if __name__ == "__main__":
    main()