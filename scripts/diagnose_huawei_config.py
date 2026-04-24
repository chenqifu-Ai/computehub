#!/usr/bin/env python3
"""
华为手机OpenClaw配置诊断脚本
主要检查LAN绑定IP问题
"""

import subprocess
import os
import time
from pathlib import Path

def run_command(cmd, timeout=10):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except Exception as e:
        return -1, "", str(e)

def check_network_connectivity():
    """检查网络连接性"""
    print("🔍 检查网络连接性...")
    
    # 检查是否能ping通
    code, stdout, stderr = run_command("ping -c 3 192.168.2.156", timeout=15)
    if code == 0:
        print("✅ 网络连接正常")
        return True
    else:
        print("❌ 网络连接失败")
        print(f"错误: {stderr}")
        return False

def check_ssh_access():
    """检查SSH访问"""
    print("\n🔍 检查SSH访问...")
    
    # 检查SSH端口
    code, stdout, stderr = run_command("nc -zv 192.168.2.156 8022", timeout=10)
    if code == 0:
        print("✅ SSH端口8022可访问")
        return True
    else:
        print("❌ SSH端口8022无法访问")
        return False

def diagnose_lan_binding_issue():
    """诊断LAN绑定问题"""
    print("\n🔍 诊断LAN绑定配置问题...")
    
    # 常见的LAN绑定问题
    common_issues = [
        "bind地址配置为127.0.0.1或localhost",
        "防火墙阻止了LAN访问", 
        "网络接口配置错误",
        "OpenClaw服务绑定到错误接口",
        "端口冲突"
    ]
    
    print("可能的问题原因:")
    for i, issue in enumerate(common_issues, 1):
        print(f"  {i}. {issue}")
    
    return common_issues

def suggest_fixes():
    """提供修复建议"""
    print("\n💡 修复建议:")
    
    fixes = [
        "1. 检查gateway.conf中的bind配置，确保不是127.0.0.1",
        "2. 确认bind地址为0.0.0.0以允许所有接口访问",
        "3. 检查防火墙设置，确保8022和18789端口开放",
        "4. 验证网络接口配置",
        "5. 重启OpenClaw服务应用配置更改"
    ]
    
    for fix in fixes:
        print(f"  {fix}")

def main():
    print("📱 华为手机OpenClaw配置诊断")
    print("=" * 50)
    
    # 检查网络连接
    network_ok = check_network_connectivity()
    
    if network_ok:
        # 检查SSH访问
        ssh_ok = check_ssh_access()
    else:
        ssh_ok = False
    
    # 诊断LAN绑定问题
    issues = diagnose_lan_binding_issue()
    
    # 提供修复建议
    suggest_fixes()
    
    print("\n🚀 下一步操作:")
    if not network_ok:
        print("  - 首先解决网络连接问题")
    elif not ssh_ok:
        print("  - 检查SSH服务是否运行")
        print("  - 验证用户名/密码是否正确")
    else:
        print("  - 通过SSH连接检查具体配置")
    
    print("\n📋 华为设备信息:")
    print("  - IP: 192.168.2.156")
    print("  - 用户名: u0_a46")
    print("  - SSH端口: 8022")
    print("  - Gateway端口: 18789")

if __name__ == "__main__":
    main()