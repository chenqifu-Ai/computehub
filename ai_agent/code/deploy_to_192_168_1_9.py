#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
192.168.1.9设备配置部署脚本
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description=""):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ 成功: {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"❌ 失败: {result.stderr.strip()}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print("⏰ 命令执行超时")
        return False, "timeout"
    except Exception as e:
        print(f"⚠️ 异常: {e}")
        return False, str(e)

def test_ssh_connection(host, port, user, password=None):
    """测试SSH连接"""
    if password:
        cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} 'echo SSH连接测试成功'"
    else:
        cmd = f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} 'echo SSH连接测试成功'"
    
    return run_command(cmd, f"测试SSH连接 {user}@{host}:{port}")

def scan_ports(host):
    """扫描常见端口"""
    common_ports = [22, 8022, 18789, 11434, 3389, 5900, 8080, 8443]
    
    for port in common_ports:
        cmd = f"timeout 2 bash -c 'echo > /dev/tcp/{host}/{port}' && echo '开放' || echo '关闭'"
        success, result = run_command(cmd, f"检查端口 {port}")
        if success and "开放" in result:
            print(f"📡 端口 {port} 可能开放")

def main():
    print("🚀 开始192.168.1.9设备配置部署")
    print("=" * 50)
    
    target_host = "192.168.1.9"
    
    # 1. 检查设备在线状态
    print("📡 检查设备在线状态...")
    success, result = run_command(f"ping -c 3 {target_host}", "Ping测试")
    if not success:
        print("❌ 设备不在线或无法访问")
        return False
    
    # 2. 扫描常见端口
    print("\n🔍 扫描常见端口...")
    scan_ports(target_host)
    
    # 3. 测试常见用户名和端口组合
    print("\n🔐 测试SSH连接...")
    
    # 常见用户名列表
    users = ["root", "admin", "ubuntu", "debian", "pi", "user", "openclaw"]
    ports = [22, 8022, 2222, 2022]
    
    found = False
    for port in ports:
        for user in users:
            success, _ = test_ssh_connection(target_host, port, user)
            if success:
                print(f"🎯 找到有效连接: {user}@{target_host}:{port}")
                found = True
                break
        if found:
            break
    
    if not found:
        print("\n❌ 未找到有效的SSH连接方式")
        print("\n💡 建议:")
        print("1. 确认设备已开启SSH服务")
        print("2. 确认防火墙设置")
        print("3. 提供正确的用户名和密码")
        print("4. 确认SSH端口号")
        
        return False
    
    print("\n✅ 设备连接测试完成")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)