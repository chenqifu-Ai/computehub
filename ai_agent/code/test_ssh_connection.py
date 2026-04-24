#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SSH连接脚本
使用密码123测试openclaw-tui用户连接
"""

import subprocess
import time

def test_ssh_connection():
    """测试SSH连接"""
    print("🔧 测试SSH连接...")
    
    # 使用sshpass进行密码自动输入测试
    try:
        result = subprocess.run(
            "sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 openclaw-tui@localhost 'echo 连接成功'",
            shell=True, capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("✅ SSH连接测试成功!")
            print(f"输出: {result.stdout}")
            return True
        else:
            print(f"❌ SSH连接失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ SSH连接超时")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def check_ssh_service():
    """检查SSH服务状态"""
    print("📊 检查SSH服务状态...")
    
    # 检查进程
    result = subprocess.run("ps aux | grep 'sshd.*8022'", shell=True, capture_output=True, text=True)
    if "sshd -p 8022" in result.stdout:
        print("✅ SSH服务正在运行")
        return True
    else:
        print("❌ SSH服务未运行")
        return False

def main():
    print("🚀 SSH连接测试工具")
    print("=" * 30)
    
    # 检查服务状态
    if not check_ssh_service():
        print("\n🔧 请先启动SSH服务:")
        print("   sshd -p 8022")
        return
    
    # 测试连接
    if test_ssh_connection():
        print("\n🎉 SSH服务配置成功!")
        print("   用户: openclaw-tui")
        print("   密码: 123") 
        print("   端口: 8022")
        print("   地址: localhost 或 设备IP")
    else:
        print("\n🔧 连接测试失败，可能需要:")
        print("   1. 确认密码正确性")
        print("   2. 检查用户权限")
        print("   3. 验证防火墙设置")

if __name__ == "__main__":
    main()