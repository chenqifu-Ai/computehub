#!/usr/bin/env python3
"""
OpenClaw部署监控系统
监控Windows设备部署状态
"""

import socket
import time
import subprocess
from datetime import datetime

def check_port(host, port, timeout=5):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def check_http_service(host, port, path='/health', timeout=5):
    """检查HTTP服务状态"""
    try:
        # 使用curl检查HTTP服务
        cmd = f"timeout {timeout} curl -s -o /dev/null -w '%{{http_code}}' http://{host}:{port}{path} || echo 'timeout'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout.strip() == '200':
            return True, "服务正常运行"
        elif result.stdout.strip() == 'timeout':
            return False, "连接超时"
        else:
            return False, f"HTTP状态: {result.stdout.strip()}"
    except:
        return False, "检查失败"

def monitor_deployment():
    """监控部署状态"""
    target_host = "192.168.2.134"
    gateway_port = 18789
    
    print("🔍 OpenClaw部署监控系统")
    print("=" * 50)
    print(f"目标设备: {target_host}")
    print(f"监控端口: {gateway_port}")
    print(f"开始时间: {datetime.now()}")
    print("=" * 50)
    
    # 监控循环
    max_attempts = 30  # 5分钟
    check_interval = 10  # 10秒
    
    for attempt in range(1, max_attempts + 1):
        print(f"\\n📊 检查尝试 {attempt}/{max_attempts}...")
        
        # 检查端口
        port_open = check_port(target_host, gateway_port)
        
        if port_open:
            print("   ✅ Gateway端口开放")
            
            # 检查服务健康
            service_ok, message = check_http_service(target_host, gateway_port)
            
            if service_ok:
                print("   🎉 OpenClaw服务正常运行!")
                print("   🌐 访问地址: http://192.168.2.134:18789")
                print("   📊 健康状态: 正常")
                print("\\n" + "=" * 50)
                print("✅ 部署成功完成!")
                return True
            else:
                print(f"   ⚠️  服务异常: {message}")
        else:
            print("   ⏳ 端口尚未开放，等待服务启动...")
        
        # 显示进度
        progress = (attempt / max_attempts) * 100
        print(f"   📈 进度: {progress:.1f}%")
        
        # 等待下一次检查
        if attempt < max_attempts:
            print(f"   ⏰ 下次检查: {check_interval}秒后...")
            time.sleep(check_interval)
    
    print("\\n" + "=" * 50)
    print("❌ 部署监控超时")
    print("💡 请手动检查Windows设备上的服务状态")
    return False

def main():
    """主函数"""
    print("🚀 启动OpenClaw部署监控...")
    
    # 先检查WinRM服务状态
    print("\\n1. 检查WinRM服务状态...")
    winrm_ok = check_port("192.168.2.134", 5985)
    
    if winrm_ok:
        print("   ✅ WinRM服务正常运行")
        print("   💡 确保已在Windows设备上执行部署命令")
    else:
        print("   ❌ WinRM服务不可用")
        print("   🔧 请检查Windows防火墙和WinRM服务设置")
    
    print("\\n2. 开始监控OpenClaw部署...")
    success = monitor_deployment()
    
    print("\\n" + "=" * 50)
    if success:
        print("🎉 监控完成: 部署成功!")
    else:
        print("⚠️  监控完成: 需要手动干预")
    
    return success

if __name__ == "__main__":
    main()