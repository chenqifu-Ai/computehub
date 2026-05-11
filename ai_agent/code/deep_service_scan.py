#!/usr/bin/env python3
"""
深度服务识别 - 通过特征分析和端口扫描确定服务类型
"""

import requests
import socket
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor

def scan_common_ports(host):
    """扫描常见服务端口"""
    common_ports = [
        22,    # SSH
        80,    # HTTP
        443,   # HTTPS
        8080,  # HTTP Alt
        8000,  # HTTP Dev
        3000,  # Node.js
        5000,  # Flask
        5432,  # PostgreSQL
        6379,  # Redis
        27017, # MongoDB
        9200,  # Elasticsearch
        5601,  # Kibana
        9090,  # Prometheus
        8282,  # 目标端口
    ]
    
    open_ports = []
    
    def check_port(port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex((host, port))
                if result == 0:
                    return port
        except:
            pass
        return None
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_port, common_ports)
        for port in results:
            if port:
                open_ports.append(port)
    
    return sorted(open_ports)

def analyze_http_service(host, port):
    """深度分析HTTP服务"""
    base_url = f"http://{host}:{port}"
    
    # 尝试获取根路径的原始响应
    try:
        response = requests.get(base_url, timeout=5, allow_redirects=False)
        
        analysis = {
            'status': response.status_code,
            'headers': dict(response.headers),
            'server': response.headers.get('Server', ''),
            'content_type': response.headers.get('Content-Type', ''),
            'body_sample': response.text[:500] if response.text else "",
            'is_json': 'application/json' in response.headers.get('Content-Type', '').lower(),
            'is_html': 'text/html' in response.headers.get('Content-Type', '').lower(),
        }
        
        # 检查特定特征
        analysis['features'] = {
            'has_api_pattern': bool(re.search(r'api|v[0-9]', response.text, re.I)),
            'has_computehub_keywords': bool(re.search(r'compute|node|task', response.text, re.I)),
            'has_go_runtime': bool(re.search(r'go|golang', response.headers.get('Server', ''), re.I)),
            'has_metrics': bool(re.search(r'metric|prometheus', response.text, re.I)),
        }
        
        return analysis
        
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}

def check_alternative_paths(host, port):
    """检查替代路径"""
    alternative_paths = [
        "/",
        "/health",
        "/healthz", 
        "/ready",
        "/status",
        "/info",
        "/version",
        "/metrics",
        "/actuator/health",
        "/debug/pprof/",
        "/v2/",
        "/v3/",
        "/admin/",
        "/api/",
        "/api/v2/",
        "/api/v3/",
    ]
    
    results = {}
    
    for path in alternative_paths:
        try:
            url = f"http://{host}:{port}{path}"
            response = requests.get(url, timeout=3, allow_redirects=False)
            results[path] = {
                'status': response.status_code,
                'content_type': response.headers.get('Content-Type', '')
            }
        except:
            results[path] = {'error': 'timeout or error'}
    
    return results

def identify_by_headers(headers):
    """通过HTTP头识别服务"""
    server = headers.get('Server', '').lower()
    content_type = headers.get('Content-Type', '').lower()
    
    service_markers = {
        'nginx': ['nginx'],
        'apache': ['apache'],
        'go_service': ['go', 'golang'],
        'nodejs': ['node', 'express'],
        'python': ['python', 'flask', 'django'],
        'java': ['java', 'tomcat', 'jetty'],
        'computehub': ['compute', 'openclaw'],
        'prometheus': ['prometheus'],
        'grafana': ['grafana'],
        'redis': ['redis'],
    }
    
    detected = []
    for service, markers in service_markers.items():
        for marker in markers:
            if marker in server:
                detected.append(service)
                break
    
    return detected

def main():
    host = "192.168.1.4"
    target_port = 8282
    
    print(f"🔍 深度服务识别 - {host}")
    print("=" * 60)
    
    # 1. 端口扫描
    print("1. 📡 扫描常见端口...")
    open_ports = scan_common_ports(host)
    print(f"   开放端口: {open_ports}")
    
    # 2. 深度分析目标端口
    print(f"2. 🔧 分析端口 {target_port}...")
    http_analysis = analyze_http_service(host, target_port)
    
    if 'error' in http_analysis:
        print(f"   ❌ HTTP分析失败: {http_analysis['error']}")
        return
    
    # 3. 检查替代路径
    print("3. 🔄 检查替代路径...")
    path_results = check_alternative_paths(host, target_port)
    
    # 4. 服务识别
    print("4. 🎯 服务类型识别...")
    service_types = identify_by_headers(http_analysis['headers'])
    
    # 输出结果
    print("\n" + "=" * 60)
    print("📊 深度分析结果")
    print("=" * 60)
    
    print(f"📍 目标: {host}:{target_port}")
    print(f"🏷️  Server: {http_analysis.get('server', 'Unknown')}")
    print(f"📄 Content-Type: {http_analysis.get('content_type', 'Unknown')}")
    print(f"🔧 检测到的服务: {', '.join(service_types) if service_types else '未知'}")
    
    print(f"\n📋 HTTP状态: {http_analysis['status']}")
    
    # 显示特征分析
    print("\n🔍 特征分析:")
    for feature, value in http_analysis['features'].items():
        print(f"   {feature}: {'✅' if value else '❌'}")
    
    # 显示路径检查结果
    print("\n🔄 路径检查 (有响应的路径):")
    for path, result in path_results.items():
        if 'status' in result and result['status'] != 404:
            print(f"   {path}: HTTP {result['status']} ({result.get('content_type', '')})")
    
    # 基于分析给出结论
    print("\n💡 结论和建议:")
    
    if http_analysis['status'] == 404 and not service_types:
        print("   ❌ 服务运行但返回404，可能是:")
        print("      - 配置错误的Web服务器")
        print("      - 自定义API服务需要特定路径")
        print("      - 服务未正确初始化")
        
    elif service_types:
        print(f"   ✅ 检测到 {service_types[0]} 服务特征")
        if 'computehub' in service_types:
            print("      - 检查ComputeHub版本和API路径配置")
        elif 'go_service' in service_types:
            print("      - 可能是Go语言编写的自定义服务")
        
    else:
        print("   🔍 服务类型不确定，建议:")
        print("      - 查看服务器日志")
        print("      - 检查服务配置文件")
        print("      - 尝试其他诊断方法")

if __name__ == "__main__":
    main()