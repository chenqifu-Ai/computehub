#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描常见服务端口
"""

import socket
import time

def scan_common_ports(ip):
    """扫描常见服务端口"""
    print(f"🔍 扫描 {ip} 的常见服务端口...")
    
    # 常见服务端口列表
    common_ports = [
        # Web服务
        80,    # HTTP
        443,   # HTTPS
        8080,  # HTTP Alt
        8443,  # HTTPS Alt
        8888,  # HTTP Alt
        
        # SSH/远程访问
        22,     # SSH
        8022,   # SSH Alt (我们的目标端口)
        2222,   # SSH Alt
        
        # 数据库
        3306,   # MySQL
        5432,   # PostgreSQL
        27017,  # MongoDB
        6379,   # Redis
        1433,   # MSSQL
        
        # 应用服务
        3000,   # Node.js
        5000,   # Flask
        8000,   # Django
        9000,   # PHP
        
        # 监控和管理
        9100,   # Node Exporter
        9090,   # Prometheus
        30000,  # Kubernetes
        
        # OpenClaw相关
        18789,  # OpenClaw Gateway
        11434,  # Ollama
        7860,   # Gradio
        
        # 其他常见
        3389,   # RDP
        5900,   # VNC
        21,     # FTP
        25,     # SMTP
        53,     # DNS
    ]
    
    open_ports = []
    
    for port in common_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((ip, port))
                if result == 0:
                    print(f"✅ 端口 {port} 开放")
                    open_ports.append(port)
                else:
                    print(f"❌ 端口 {port} 关闭")
        except:
            print(f"⚠️  端口 {port} 扫描错误")
    
    return open_ports

def main():
    target_ip = "192.168.1.9"
    
    print("🚀 常见服务端口扫描")
    print("=" * 40)
    
    open_ports = scan_common_ports(target_ip)
    
    print(f"\n🎯 扫描完成!")
    print(f"目标: {target_ip}")
    print(f"开放的常见服务端口: {open_ports}")
    
    # 保存结果
    with open(f"/root/.openclaw/workspace/ai_agent/results/common_ports_{target_ip}.txt", "w") as f:
        f.write(f"常见服务端口扫描结果 - {target_ip}\n")
        f.write(f"扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"开放端口: {open_ports}\n")
        
        # 端口描述
        port_descriptions = {
            22: "SSH",
            80: "HTTP",
            443: "HTTPS", 
            8022: "SSH Alt",
            18789: "OpenClaw Gateway",
            11434: "Ollama",
            8080: "HTTP Alt",
            8443: "HTTPS Alt",
            3306: "MySQL",
            5432: "PostgreSQL",
            27017: "MongoDB",
            6379: "Redis"
        }
        
        f.write("\n端口服务说明:\n")
        for port in open_ports:
            desc = port_descriptions.get(port, "未知服务")
            f.write(f"端口 {port}: {desc}\n")
    
    print(f"📝 结果已保存到: /root/.openclaw/workspace/ai_agent/results/common_ports_{target_ip}.txt")

if __name__ == "__main__":
    main()