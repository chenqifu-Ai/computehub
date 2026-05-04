#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细端口测试脚本 - 8022端口诊断
"""

import socket
import subprocess
import time

def test_port(host, port):
    """测试端口连接"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            result = s.connect_ex((host, port))
            return result == 0
    except:
        return False

def test_ssh_with_passwords(host, port, users):
    """测试带密码的SSH连接"""
    common_passwords = [
        "123456", "password", "123456789", "12345678", "12345",
        "1234567890", "admin", "root", "ubuntu", "debian",
        "raspberry", "pi", "openclaw", "123", "1234"
    ]
    
    for user in users:
        for password in common_passwords:
            cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} 'echo success' 2>/dev/null"
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
                if result.returncode == 0:
                    return True, user, password
            except:
                continue
    
    return False, None, None

def main():
    host = "192.168.1.9"
    port = 8022
    
    print(f"🔍 详细测试 {host}:{port}")
    print("=" * 40)
    
    # 测试端口是否开放
    print("1. 测试端口连接性...")
    port_open = test_port(host, port)
    print(f"   端口 {port} {'✅ 开放' if port_open else '❌ 关闭'}")
    
    if not port_open:
        print("\n❌ 端口未开放，可能的原因:")
        print("   - SSH服务未运行")
        print("   - 防火墙阻止了连接")
        print("   - 端口配置错误")
        print("   - 设备不在线或网络问题")
        return
    
    print("\n2. 测试常见用户名...")
    users = ["root", "admin", "ubuntu", "user", "pi", "openclaw"]
    
    for user in users:
        cmd = f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} 'echo test' 2>/dev/null"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            if result.returncode == 0:
                print(f"   ✅ {user} - 无需密码")
                return
            elif "Permission denied" in result.stderr:
                print(f"   🔐 {user} - 需要密码")
            else:
                print(f"   ❌ {user} - 连接失败")
        except:
            print(f"   ⏰ {user} - 超时")
    
    print("\n3. 测试常见密码组合...")
    success, user, password = test_ssh_with_passwords(host, port, users)
    
    if success:
        print(f"   ✅ 找到有效凭证: {user}/{password}")
    else:
        print("   ❌ 未找到有效密码")
        print("\n💡 建议:")
        print("   - 确认SSH服务正在运行")
        print("   - 检查防火墙设置")
        print("   - 提供正确的用户名和密码")

if __name__ == "__main__":
    main()