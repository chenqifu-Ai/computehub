#!/usr/bin/env python3
"""
详细端口检查工具
"""

import socket
import sys
import time

def check_port_with_retry(ip, port, retries=3, timeout=2):
    """带重试的端口检查"""
    for attempt in range(retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                return True, f"端口 {port} 开放 (第{attempt+1}次尝试)"
            else:
                print(f"第{attempt+1}次尝试: 端口 {port} 关闭 (错误码: {result})")
                
        except Exception as e:
            print(f"第{attempt+1}次尝试: 检查错误 - {e}")
        
        if attempt < retries - 1:
            time.sleep(1)
    
    return False, f"端口 {port} 关闭 (所有{retries}次尝试)"

def main():
    ip = "10.35.204.26"
    ports = [8022, 22, 2222, 2022]  # 检查多个SSH端口
    
    print(f"🔍 详细检查设备 {ip} 的端口状态")
    print("=" * 50)
    
    any_open = False
    
    for port in ports:
        open, message = check_port_with_retry(ip, port)
        if open:
            print(f"✅ {message}")
            any_open = True
        else:
            print(f"❌ {message}")
    
    print("=" * 50)
    
    if any_open:
        print("🎯 发现开放端口，可以尝试连接")
    else:
        print("⚠️  所有SSH端口都关闭")
        print("💡 建议在设备上启动SSH服务:")
        print("   在Termux中运行: sshd -p 8022")

if __name__ == "__main__":
    main()