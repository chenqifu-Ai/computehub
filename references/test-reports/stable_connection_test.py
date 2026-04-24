#!/usr/bin/env python3
"""
稳定连接测试脚本
"""

import subprocess
import time

def test_ssh_connection(ip, port, user, password, retries=3):
    """测试SSH连接稳定性"""
    for attempt in range(retries):
        try:
            cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{ip} 'echo 连接测试成功; exit 0'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, f"第{attempt+1}次尝试成功"
            else:
                print(f"第{attempt+1}次尝试失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"第{attempt+1}次尝试超时")
        except Exception as e:
            print(f"第{attempt+1}次尝试异常: {e}")
        
        if attempt < retries - 1:
            time.sleep(2)  # 等待2秒后重试
    
    return False, "所有尝试都失败"

def main():
    ip = "10.35.204.26"
    port = 8022
    user = "u0_a46"
    password = "123"
    
    print(f"🔗 测试SSH连接稳定性: {user}@{ip}:{port}")
    print("=" * 50)
    
    success, message = test_ssh_connection(ip, port, user, password)
    
    if success:
        print(f"✅ {message}")
        print("🎯 连接稳定，可以继续装机")
        return True
    else:
        print(f"❌ {message}")
        print("⚠️  连接不稳定，建议:")
        print("   1. 检查设备网络状态")
        print("   2. 确认SSH服务运行")
        print("   3. 检查防火墙设置")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)