#!/usr/bin/env python3
"""
检查常见SSH端口
"""

import socket
import sys

def check_ports(ip, ports):
    """检查多个端口"""
    print(f"🔍 检查设备 {ip} 的SSH端口:")
    print("=" * 40)
    
    open_ports = []
    
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                status = "✅ 开放"
                open_ports.append(port)
            else:
                status = "❌ 关闭"
            
            print(f"端口 {port}: {status}")
            
        except Exception as e:
            print(f"端口 {port}: ❌ 错误 ({e})")
    
    return open_ports

def main():
    if len(sys.argv) < 2:
        print("用法: python check_ssh_ports.py <IP>")
        sys.exit(1)
    
    ip = sys.argv[1]
    
    # 常见SSH端口
    common_ports = [22, 8022, 2222, 2022, 1022, 8023, 8024]
    
    open_ports = check_ports(ip, common_ports)
    
    print("\n" + "=" * 40)
    if open_ports:
        print(f"🎯 发现开放端口: {', '.join(map(str, open_ports))}")
        print("💡 可以尝试这些端口进行SSH连接")
    else:
        print("❌ 未发现开放SSH端口")
        print("⚠️  可能的原因:")
        print("   - SSH服务未运行")
        print("   - 防火墙阻止连接")
        print("   - 设备配置问题")

if __name__ == "__main__":
    main()