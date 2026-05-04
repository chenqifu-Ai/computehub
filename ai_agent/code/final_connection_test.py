#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终连接测试脚本
测试192.168.1.9设备的SSH连接
"""

import subprocess
import time

def test_connection():
    """测试连接"""
    print("🔧 开始全面连接测试...")
    
    # 1. 测试网络连通性
    print("1. 测试网络连通性...")
    ping_result = subprocess.run("ping -c 2 192.168.1.9", shell=True, capture_output=True)
    if ping_result.returncode == 0:
        print("   ✅ 网络连通性正常")
    else:
        print("   ❌ 网络不通")
        return False
    
    # 2. 测试端口8022
    print("2. 测试端口8022...")
    port_test = subprocess.run(
        "timeout 2 bash -c 'echo > /dev/tcp/192.168.1.9/8022'",
        shell=True, capture_output=True
    )
    if port_test.returncode == 0:
        print("   ✅ 端口8022开放")
    else:
        print("   ❌ 端口8022关闭")
        return False
    
    # 3. 测试SSH连接
    print("3. 测试SSH连接...")
    try:
        ssh_test = subprocess.run(
            "timeout 5 ssh -o StrictHostKeyChecking=no -p 8022 openclaw-tui@192.168.1.9 'echo 测试成功'",
            shell=True, capture_output=True, text=True
        )
        
        if ssh_test.returncode == 0:
            print("   ✅ SSH连接成功!")
            print(f"     输出: {ssh_test.stdout}")
            return True
        else:
            print(f"   ❌ SSH连接失败: {ssh_test.stderr}")
            
    except subprocess.TimeoutExpired:
        print("   ⚠️  SSH连接超时")
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
    
    return False

def main():
    print("🚀 最终连接测试")
    print("=" * 40)
    
    if test_connection():
        print("\n🎉 连接测试完全成功!")
        print("   设备: 192.168.1.9")
        print("   端口: 8022")
        print("   用户: openclaw-tui")
        print("   状态: ✅ 就绪")
    else:
        print("\n🔧 需要进一步调试:")
        print("   1. 确认192.168.1.9设备上SSH服务运行")
        print("   2. 确认用户openclaw-tui密码正确")
        print("   3. 检查防火墙设置")
        print("   4. 验证网络配置")

if __name__ == "__main__":
    main()