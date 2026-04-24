#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
继续端口扫描脚本
从401端口继续扫描到1000
"""

import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def scan_port(ip, port):
    """扫描单个端口"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((ip, port))
            if result == 0:
                print(f"✅ 端口 {port} 开放")
                return port
            else:
                if port % 100 == 0:
                    print(f"进度: {port}/1000")
                return None
    except:
        return None

def continue_port_scan(ip, start_port=401, end_port=1000):
    """继续端口扫描"""
    print(f"📡 继续扫描 {ip} 的端口 {start_port}-{end_port}...")
    
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for port in range(start_port, end_port + 1):
            futures.append(executor.submit(scan_port, ip, port))
        
        for future in futures:
            result = future.result()
            if result:
                open_ports.append(result)
    
    return sorted(open_ports)

def main():
    target_ip = "192.168.1.9"
    
    print("🚀 继续端口扫描任务")
    print("=" * 40)
    
    # 继续扫描 401-1000 端口
    open_ports = continue_port_scan(target_ip, 401, 1000)
    
    print(f"\n🎯 扫描完成!")
    print(f"目标: {target_ip}")
    print(f"开放端口: {open_ports}")
    
    # 特别关注常用端口
    common_ports = [22, 80, 443, 8080, 8443, 3306, 5432, 6379, 27017]
    found_common = [p for p in open_ports if p in common_ports]
    
    if found_common:
        print(f"🔍 发现的常用服务端口: {found_common}")
    
    # 保存结果
    with open(f"/root/.openclaw/workspace/ai_agent/results/port_scan_{target_ip}.txt", "w") as f:
        f.write(f"端口扫描结果 - {target_ip}\n")
        f.write(f"扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"开放端口: {open_ports}\n")
        f.write(f"常用服务端口: {found_common}\n")
    
    print(f"📝 结果已保存到: /root/.openclaw/workspace/ai_agent/results/port_scan_{target_ip}.txt")

if __name__ == "__main__":
    main()