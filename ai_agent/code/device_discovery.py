#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
192.168.1.9设备深度探测脚本
"""

import subprocess
import sys
import socket
import time
from concurrent.futures import ThreadPoolExecutor

def test_port(host, port):
    """测试单个端口"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex((host, port))
            return port, result == 0
    except:
        return port, False

def mass_port_scan(host, start_port=1, end_port=1000, max_workers=50):
    """批量端口扫描"""
    print(f"🔍 扫描{host}的端口{start_port}-{end_port}...")
    
    open_ports = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for port in range(start_port, end_port + 1):
            futures.append(executor.submit(test_port, host, port))
        
        for i, future in enumerate(futures):
            port, is_open = future.result()
            if is_open:
                open_ports.append(port)
                print(f"📡 发现开放端口: {port}")
            
            # 进度显示
            if (i + 1) % 100 == 0:
                print(f"进度: {i+1}/{end_port-start_port+1}")
    
    return open_ports

def detect_os(host):
    """尝试探测操作系统类型"""
    print("🖥️  尝试探测操作系统...")
    
    # TTL值分析
    try:
        result = subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True, text=True)
        if "ttl=" in result.stdout.lower():
            ttl_line = [line for line in result.stdout.split('\n') if 'ttl=' in line.lower()]
            if ttl_line:
                ttl = int(ttl_line[0].split('ttl=')[1].split()[0])
                print(f"📊 TTL值: {ttl}")
                
                if ttl <= 64:
                    print("🤖 可能是Linux/Unix系统")
                    return "linux"
                elif 65 <= ttl <= 128:
                    print("🪟 可能是Windows系统")
                    return "windows"
                else:
                    print("❓ 未知操作系统")
                    return "unknown"
    except:
        pass
    
    return "unknown"

def check_common_services(host, ports):
    """检查常见服务"""
    service_map = {
        21: "FTP",
        22: "SSH", 
        23: "Telnet",
        25: "SMTP",
        53: "DNS",
        80: "HTTP",
        443: "HTTPS",
        445: "SMB",
        3389: "RDP",
        5900: "VNC",
        6379: "Redis",
        27017: "MongoDB"
    }
    
    print("🔧 检查常见服务...")
    for port in ports:
        if port in service_map:
            service = service_map[port]
            print(f"  端口 {port}: {service}服务")

def main():
    host = "192.168.1.9"
    
    print(f"🚀 开始深度探测 {host}")
    print("=" * 50)
    
    # 检查设备在线状态
    print("📡 检查设备状态...")
    result = subprocess.run(f"ping -c 2 {host}", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ 设备不在线")
        return
    
    # 探测操作系统
    os_type = detect_os(host)
    
    # 扫描常见端口范围
    open_ports = mass_port_scan(host, 1, 1000)
    
    print(f"\n📊 探测结果汇总:")
    print(f"📍 设备: {host}")
    print(f"🖥️  操作系统: {os_type}")
    print(f"🚪 开放端口: {open_ports}")
    
    if open_ports:
        check_common_services(host, open_ports)
        print(f"\n💡 发现开放端口，可以尝试连接:")
        for port in open_ports:
            print(f"  端口 {port}: 可能运行着某种服务")
    else:
        print("\n❌ 未发现任何开放端口")
        print("\n🔧 建议操作:")
        print("1. 确认设备已开机并联网")
        print("2. 检查防火墙设置")
        print("3. 确认设备运行了什么服务")
        print("4. 提供设备的连接方式")

if __name__ == "__main__":
    main()