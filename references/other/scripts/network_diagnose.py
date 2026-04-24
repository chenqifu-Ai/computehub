#!/usr/bin/env python3
"""
网络诊断工具 - 检查设备连接问题
"""

import subprocess
import sys
import socket
import time

def check_ip_validity(ip):
    """检查IP地址是否有效"""
    try:
        socket.inet_aton(ip)
        # 检查是否是广播地址
        if ip.endswith('.255') or ip.endswith('.0'):
            return False, "广播或网络地址"
        return True, "有效IP"
    except socket.error:
        return False, "无效IP格式"

def check_port_connectivity(ip, port, timeout=3):
    """检查端口连通性"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0, "端口开放" if result == 0 else f"端口关闭 (错误码: {result})"
    except Exception as e:
        return False, f"连接错误: {e}"

    """检查SSH服务"""
    try:
        # 使用sshpass测试连接
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, "SSH连接成功"
        else:
            return False, f"SSH连接失败: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "SSH连接超时"
    except Exception as e:
        return False, f"SSH检查错误: {e}"

    """完整设备诊断"""
    print(f"🔍 开始诊断设备: {username}@{ip}:{port}")
    print("=" * 50)
    
    # 1. 检查IP有效性
    ip_valid, ip_msg = check_ip_validity(ip)
    print(f"🌐 IP检查: {'✅' if ip_valid else '❌'} {ip_msg}")
    
    if not ip_valid:
        print(f"💡 建议: 请提供正确的设备IP地址 (不是广播地址 {ip})")
        return False
    
    # 2. 检查端口连通性
    port_open, port_msg = check_port_connectivity(ip, port)
    print(f"🚪 端口检查: {'✅' if port_open else '❌'} {port_msg}")
    
    # 3. 检查SSH服务
    print(f"🔑 SSH检查: {'✅' if ssh_ok else '❌'} {ssh_msg}")
    
    print("=" * 50)
    
    if ip_valid and port_open and ssh_ok:
        print("🎉 设备连接正常，可以开始部署!")
        return True
    else:
        print("⚠️  设备连接存在问题，请检查:")
        if not port_open:
            print("   - 确认设备SSH服务正在运行")
            print("   - 检查防火墙设置")
        if not ssh_ok:
            print("   - 确认用户名密码正确")
            print("   - 检查SSH配置")
        return False

def main():
    if len(sys.argv) < 5:
        print("用法: python network_diagnose.py <IP> <端口> <用户名> <密码>")
        print("示例: python network_diagnose.py 192.168.1.100 8022 u0_a207 123")
        sys.exit(1)
    
    ip = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()