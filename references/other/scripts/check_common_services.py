#!/usr/bin/env python3
"""
检查常见服务端口
"""

import socket
import sys

def check_service_ports(ip, port_services):
    """检查常见服务端口"""
    print(f"🔍 检查设备 {ip} 的服务端口:")
    print("=" * 50)
    
    open_services = []
    
    for port, service in port_services.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                status = "✅ 开放"
                open_services.append((port, service))
            else:
                status = "❌ 关闭"
            
            print(f"{service} (端口 {port}): {status}")
            
        except Exception as e:
            print(f"{service} (端口 {port}): ❌ 错误 ({e})")
    
    return open_services

def main():
    if len(sys.argv) < 2:
        print("用法: python check_common_services.py <IP>")
        sys.exit(1)
    
    ip = sys.argv[1]
    
    # 常见服务端口
    common_services = {
        22: "SSH",
        8022: "SSH(备用)",
        80: "HTTP",
        443: "HTTPS", 
        8080: "HTTP代理",
        8000: "HTTP备用",
        3000: "Node.js",
        18789: "OpenClaw Gateway",
        11434: "Ollama",
        9000: "Portainer",
        2375: "Docker",
        2376: "Docker TLS"
    }
    
    open_services = check_service_ports(ip, common_services)
    
    print("\n" + "=" * 50)
    if open_services:
        print(f"🎯 发现开放服务: {len(open_services)} 个")
        for port, service in open_services:
            print(f"   • {service} (端口 {port})")
    else:
        print("❌ 未发现任何开放服务")
        print("⚠️  设备可能:")
        print("   - 未运行任何网络服务")
        print("   - 防火墙阻止所有连接")
        print("   - 网络配置问题")

if __name__ == "__main__":
    main()