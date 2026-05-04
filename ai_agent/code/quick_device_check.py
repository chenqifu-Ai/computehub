#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速设备检查脚本 - 重点检查常见服务
"""

import subprocess
import socket
import sys

def quick_port_check(host, ports):
    """快速端口检查"""
    open_ports = []
    
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                if result == 0:
                    open_ports.append(port)
                    print(f"✅ 端口 {port} 开放")
                else:
                    print(f"❌ 端口 {port} 关闭")
        except:
            print(f"⚠️  端口 {port} 检查失败")
    
    return open_ports

def check_device_info(host):
    """检查设备基本信息"""
    print(f"🔍 检查设备 {host} 基本信息...")
    
    # Ping测试
    result = subprocess.run(f"ping -c 2 {host}", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 设备在线")
        # 提取TTL信息
        lines = result.stdout.split('\n')
        for line in lines:
            if 'ttl=' in line.lower():
                ttl = line.split('ttl=')[1].split()[0]
                print(f"📊 TTL值: {ttl}")
                
                # 根据TTL猜测操作系统
                ttl_val = int(ttl)
                if ttl_val <= 64:
                    print("🤖 猜测: Linux/Unix系统")
                elif 65 <= ttl_val <= 128:
                    print("🪟 猜测: Windows系统")
                else:
                    print("❓ 猜测: 其他系统")
                break
    else:
        print("❌ 设备不在线")
        return False
    
    return True

def main():
    host = "192.168.1.9"
    
    print(f"🚀 快速检查 {host}")
    print("=" * 40)
    
    # 检查设备状态
    if not check_device_info(host):
        return
    
    print("\n🔧 检查常见服务端口:")
    
    # 常见服务端口
    common_ports = [
        21,    # FTP
        22,    # SSH
        23,    # Telnet  
        25,    # SMTP
        53,    # DNS
        80,    # HTTP
        443,   # HTTPS
        445,   # SMB
        1433,  # MSSQL
        3306,  # MySQL
        3389,  # RDP
        5900,  # VNC
        6379,  # Redis
        27017, # MongoDB
        18789, # OpenClaw Gateway
        11434  # Ollama
    ]
    
    open_ports = quick_port_check(host, common_ports)
    
    print(f"\n📊 结果汇总:")
    print(f"📍 设备: {host}")
    print(f"🚪 开放端口: {open_ports}")
    
    if not open_ports:
        print("\n❌ 未发现任何开放服务")
        print("\n💡 建议:")
        print("1. 确认设备已开启所需服务")
        print("2. 提供设备的连接方式（RDP/VNC/其他）")
        print("3. 确认防火墙设置")
        print("4. 检查设备是否运行了特殊服务")
    else:
        print("\n🎯 发现开放服务，可以尝试连接")

if __name__ == "__main__":
    main()