#!/usr/bin/env python3
"""
工作电脑远程控制脚本 - 192.168.2.134
"""

import socket
import os
from datetime import datetime

TARGET_IP = "192.168.2.134"
PORTS_TO_CHECK = [135, 139, 445, 3389, 5985, 5986]

def check_port(ip, port, timeout=2):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("="*60)
    print(f"💻 工作电脑远程控制分析 - {TARGET_IP}")
    print("="*60)
    
    # 扫描端口
    print(f"🔍 开始扫描 {TARGET_IP} ...")
    open_ports = []
    
    for port in PORTS_TO_CHECK:
        is_open = check_port(TARGET_IP, port)
        status = "✅ 开放" if is_open else "❌ 关闭"
        print(f"端口 {port}: {status}")
        if is_open:
            open_ports.append(port)
    
    # 分析结果
    print("\n🔒 安全状况分析:")
    if 445 in open_ports:
        print("⚠️  SMB端口(445)开放 - 可尝试文件共享访问")
    if 3389 in open_ports:
        print("✅  RDP端口(3389)开放 - 可直接远程桌面连接")
    else:
        print("ℹ️  RDP端口(3389)关闭 - 需要启用远程桌面服务")
    
    # 生成访问方案
    print("\n🎯 立即执行方案:")
    
    if 3389 in open_ports:
        print("1. 直接远程桌面连接:")
        print(f"   mstsc /v:{TARGET_IP}")
        print("   用户名: 您的工作账户")
        print("   密码: 您的工作密码")
    
    if 445 in open_ports:
        print("\n2. SMB文件共享访问:")
        print(f"   Windows资源管理器: \\\\{TARGET_IP}")
        print(f"   或: net use \\\\{TARGET_IP}\\c$ /user:用户名 密码")
    
    # 如果RDP未开放但SMB开放，提供启用脚本
    if 445 in open_ports and 3389 not in open_ports:
        print("\n3. 启用远程桌面脚本:")
        print("   创建enable_rdp.bat并执行:")
        print('''    @echo off
    reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f
    netsh advfirewall firewall set rule group="remote desktop" new enable=Yes
    echo 远程桌面已启用！''')
    
    print("\n✅ 分析完成！请根据上述方案立即执行。")

if __name__ == "__main__":
    main()