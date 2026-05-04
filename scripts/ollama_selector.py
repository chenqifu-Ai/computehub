#!/usr/bin/env python3
"""
Ollama服务智能选择器
优先使用云端服务，自动故障转移
"""

import requests
import time
from datetime import datetime

class OllamaSelector:
    def __init__(self):
        self.servers = [
            {
                'name': '云端服务',
                'url': 'https://ollama.com',
                'priority': 1,
                'timeout': 10
            },
            {
                'name': '本地主服务器', 
                'url': 'http://192.168.1.7:11434',
                'priority': 2,
                'timeout': 5
            },
            {
                'name': '本地备用服务器',
                'url': 'http://192.168.1.19:11434', 
                'priority': 3,
                'timeout': 5
            }
        ]
        
        # 按优先级排序
        self.servers.sort(key=lambda x: x['priority'])
        
    def check_server_health(self, server):
        """检查服务器健康状态"""
        try:
            start_time = time.time()
            
            # 尝试访问API端点
            if server['url'] == 'https://ollama.com':
                # 云端服务检查
                response = requests.get(server['url'], timeout=server['timeout'])
                status = response.status_code == 200
            else:
                # 本地服务检查
                response = requests.get(f"{server['url']}/api/tags", timeout=server['timeout'])
                status = response.status_code == 200
            
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            return {
                'status': status,
                'response_time': response_time,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'status': False,
                'error': str(e),
                'response_time': None,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def get_best_server(self):
        """获取最佳可用服务器"""
        print("🔍 检查Ollama服务器状态...")
        
        best_server = None
        
        for server in self.servers:
            print(f"  检查 {server['name']} ({server['url']})...")
            
            health = self.check_server_health(server)
            
            if health['status']:
                print(f"    ✅ 正常 (响应时间: {health['response_time']:.0f}ms)")
                best_server = server
                best_server['health'] = health
                break
            else:
                print(f"    ❌ 失败: {health.get('error', '未知错误')}")
        
        return best_server
    
    def get_server_status(self):
        """获取所有服务器状态"""
        status_report = []
        
        for server in self.servers:
            health = self.check_server_health(server)
            status_report.append({
                'server': server,
                'health': health
            })
        
        return status_report

def main():
    selector = OllamaSelector()
    
    print("🤖 Ollama服务智能选择器")
    print("=" * 50)
    
    # 获取最佳服务器
    best_server = selector.get_best_server()
    
    print("\n" + "=" * 50)
    
    if best_server:
        print(f"🎯 推荐使用: {best_server['name']}")
        print(f"   📍 地址: {best_server['url']}")
        print(f"   ⚡ 响应: {best_server['health']['response_time']:.0f}ms")
        print(f"   ⏰ 检查时间: {best_server['health']['timestamp']}")
        print(f"   🏆 优先级: {best_server['priority']}")
    else:
        print("❌ 所有Ollama服务器均不可用")
        print("💡 建议: 检查网络连接或稍后重试")
    
    print("=" * 50)

if __name__ == "__main__":
    main()