#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw安装调试脚本
"""

import subprocess
import sys

def run_cmd(cmd, description):
    """运行命令并返回结果"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ 成功: {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"❌ 失败: {result.stderr.strip()}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print("⏰ 超时")
        return False, "timeout"
    except Exception as e:
        print(f"⚠️ 异常: {e}")
        return False, str(e)

def debug_openclaw_install():
    """调试OpenClaw安装"""
    host = "192.168.1.9"
    
    print("🚀 OpenClaw安装调试")
    print("=" * 40)
    
    # 1. 检查设备在线状态
    print("1. 检查设备连接...")
    success, result = run_cmd(f"ping -c 2 {host}", "Ping测试")
    if not success:
        print("❌ 设备不在线")
        return False
    
    # 2. 尝试常见调试方法
    methods = [
        # 方法1: 检查Gateway服务
        (f"curl -s http://{host}:18789/health --connect-timeout 5", "Gateway健康检查"),
        
        # 方法2: 检查SSH服务
        (f"ssh -o StrictHostKeyChecking=no -p 8022 root@{host} 'echo SSH可用' 2>/dev/null", "SSH连接测试"),
        
        # 方法3: 检查其他端口
        (f"curl -s http://{host}:8080 --connect-timeout 3 2>/dev/null", "HTTP端口检查"),
        
        # 方法4: 检查网络连通性
        (f"traceroute -m 3 {host} 2>/dev/null | tail -3", "网络路由检查")
    ]
    
    for cmd, desc in methods:
        success, result = run_cmd(cmd, desc)
        if success:
            print(f"   📋 结果: {result}")
    
    print("\n💡 调试建议:")
    print("1. 确认OpenClaw Gateway服务已启动")
    print("2. 检查防火墙设置")
    print("3. 确认端口18789已开放")
    print("4. 查看服务日志: openclaw gateway logs")
    print("5. 重启服务: openclaw gateway restart")
    
    return True

if __name__ == "__main__":
    debug_openclaw_install()