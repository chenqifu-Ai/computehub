#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速服务检查 - 192.168.1.9设备
"""

import subprocess

def check_service(host, port, service_name):
    """检查特定服务"""
    try:
        # 测试端口连接
        cmd = f"timeout 2 bash -c 'echo > /dev/tcp/{host}/{port}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
        
        if result.returncode == 0:
            print(f"✅ {service_name} (端口{port}) - 可能开放")
            return True
        else:
            print(f"❌ {service_name} (端口{port}) - 关闭")
            return False
    except:
        print(f"⚠️ {service_name} (端口{port}) - 检查失败")
        return False

def main():
    host = "192.168.1.9"
    
    print(f"🔍 快速服务检查 - {host}")
    print("=" * 40)
    
    # 常见服务端口
    services = [
        (22, "SSH"),
        (8022, "SSH(自定义)"),
        (18789, "OpenClaw Gateway"),
        (11434, "Ollama"),
        (80, "HTTP"),
        (443, "HTTPS"),
        (3389, "RDP"),
        (5900, "VNC"),
        (8080, "HTTP-Alt"),
        (8443, "HTTPS-Alt")
    ]
    
    any_open = False
    for port, service in services:
        if check_service(host, port, service):
            any_open = True
    
    print("\n" + "=" * 40)
    if any_open:
        print("🎯 发现有服务开放，请提供连接方式")
    else:
        print("❌ 未发现任何服务开放")
        print("💡 设备可能需要配置网络服务")

if __name__ == "__main__":
    main()