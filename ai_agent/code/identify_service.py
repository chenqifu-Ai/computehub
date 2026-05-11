#!/usr/bin/env python3
"""
192.168.1.4 服务类型识别脚本
通过多种方法识别端口8282运行的服务类型
"""

import requests
import socket
import subprocess
import json
from urllib.parse import urljoin

def test_http_methods(host, port):
    """测试各种HTTP方法和路径"""
    base_url = f"http://{host}:{port}"
    
    test_cases = [
        # 标准 API 路径
        ("/", "GET"),
        ("/api/", "GET"),
        ("/api/v1/", "GET"),
        ("/api/v1/status", "GET"),
        ("/v1/", "GET"),
        ("/status", "GET"),
        ("/health", "GET"),
        ("/healthz", "GET"),
        ("/ready", "GET"),
        
        # 常见服务路径
        ("/metrics", "GET"),           # Prometheus
        ("/actuator/health", "GET"),   # Spring Boot
        ("/debug/pprof/", "GET"),      # Go pprof
        ("/version", "GET"),           # 版本信息
        ("/info", "GET"),              # 服务信息
        
        # ComputeHub 特定路径
        ("/api/v1/nodes", "GET"),
        ("/api/v1/tasks", "POST"),
        ("/api/v1/nodes/register", "POST"),
    ]
    
    results = {}
    
    for path, method in test_cases:
        try:
            url = urljoin(base_url, path)
            if method == "GET":
                response = requests.get(url, timeout=5, allow_redirects=False)
            elif method == "POST":
                response = requests.post(url, timeout=5, json={"test": "data"})
            else:
                continue
                
            results[path] = {
                'status': response.status_code,
                'headers': dict(response.headers),
                'body_preview': response.text[:200] if response.text else ""
            }
            
        except requests.exceptions.RequestException as e:
            results[path] = {'error': str(e)}
        except Exception as e:
            results[path] = {'error': f"Unexpected error: {e}"}
    
    return results

def test_socket_protocol(host, port):
    """测试原始socket协议"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            
            # 发送一些测试数据
            s.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
            response = s.recv(1024)
            
            return {
                'raw_response': response.decode('utf-8', errors='ignore')[:500],
                'success': True
            }
    except Exception as e:
        return {'error': str(e), 'success': False}

def check_service_banner(host, port):
    """检查服务banner信息"""
    try:
        # 使用 curl 获取详细响应
        cmd = f"curl -s -I -X GET http://{host}:{port}/"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return {
                'headers': result.stdout,
                'success': True
            }
        else:
            return {'error': result.stderr, 'success': False}
    except Exception as e:
        return {'error': str(e), 'success': False}

def identify_service_type(results):
    """根据测试结果识别服务类型"""
    # 分析响应特征
    service_indicators = {
        'computehub': ['computehub', 'nodes', 'tasks', 'api/v1'],
        'prometheus': ['metrics', 'prometheus'],
        'spring_boot': ['actuator', 'spring'],
        'go_service': ['go/', 'pprof', 'golang'],
        'nginx': ['nginx', 'server: nginx'],
        'apache': ['apache', 'server: apache'],
        'custom_api': ['application/json', 'api'],
        'web_server': ['html', 'http', 'server']
    }
    
    detected_services = []
    
    for path, data in results.items():
        if 'headers' in data:
            headers = data['headers']
            body = data.get('body_preview', '').lower()
            
            # 检查 Server header
            server_header = headers.get('Server', '').lower()
            
            for service, indicators in service_indicators.items():
                for indicator in indicators:
                    if (indicator in server_header or 
                        indicator in body or
                        indicator in path.lower()):
                        if service not in detected_services:
                            detected_services.append(service)
    
    return detected_services

def main():
    host = "192.168.1.4"
    port = 8282
    
    print(f"🔍 开始识别 {host}:{port} 服务类型")
    print("=" * 50)
    
    # 1. 测试HTTP方法
    print("1. HTTP方法测试...")
    http_results = test_http_methods(host, port)
    
    # 2. 原始socket测试
    print("2. 原始协议测试...")
    socket_result = test_socket_protocol(host, port)
    
    # 3. 服务banner检查
    print("3. 服务banner检查...")
    banner_result = check_service_banner(host, port)
    
    # 4. 识别服务类型
    print("4. 服务类型分析...")
    service_types = identify_service_type(http_results)
    
    # 输出结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    print(f"📍 目标: {host}:{port}")
    print(f"🔧 检测到的服务类型: {', '.join(service_types) if service_types else '未知'}")
    
    print("\n📋 HTTP响应样例:")
    for path, result in list(http_results.items())[:5]:  # 显示前5个
        if 'status' in result:
            print(f"  {path}: HTTP {result['status']}")
        elif 'error' in result:
            print(f"  {path}: ERROR - {result['error']}")
    
    if socket_result.get('success'):
        print(f"\n🔌 原始响应: {socket_result['raw_response'][:100]}...")
    
    if banner_result.get('success'):
        print(f"\n🏷️  服务Header:\n{banner_result['headers']}")
    
    # 基于特征给出建议
    print("\n💡 建议下一步:")
    if not service_types:
        print("  - 尝试其他端口扫描")
        print("  - 检查是否为自定义服务")
        print("  - 查看服务日志确认类型")
    elif 'computehub' in service_types:
        print("  - 确认ComputeHub版本和配置")
        print("  - 检查API路径是否正确")
    else:
        for service in service_types:
            print(f"  - 针对{service}服务进行进一步测试")

if __name__ == "__main__":
    main()