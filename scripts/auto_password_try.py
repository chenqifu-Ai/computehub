#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化密码尝试脚本
尝试常见密码组合
"""

import subprocess
import time

def try_password(password):
    """尝试一个密码"""
    try:
        result = subprocess.run([
            'sshpass', '-p', password,
            'ssh', '-p', '8022',
            'u0_a207@192.168.1.19',
            'echo "密码测试成功"'
        ], capture_output=True, text=True, timeout=8)
        
        if result.returncode == 0:
            return True, "成功"
        else:
            return False, result.stderr.strip()
            
    except Exception as e:
        return False, f"异常: {e}"

def main():
    """主函数"""
    print("🔐 自动化密码尝试")
    print("====================")
    
    # 常见密码列表
    passwords = [
        "123", "123456", "password", "admin", "root",
        "", "000000", "111111", "654321", "qwerty",
        "openclaw", "termux", "android", "mi", "xiaomi",
        "u0_a207", "a207", "207"
    ]
    
    success_password = None
    
    for pwd in passwords:
        print(f"尝试密码: {pwd if pwd else '[空密码]'}", end="")
        
        success, message = try_password(pwd)
        
        if success:
            print(" ✅ 成功!")
            success_password = pwd
            break
        else:
            if "Permission denied" in message:
                print(" ❌ 权限被拒绝")
            elif "Connection refused" in message:
                print(" ❌ 连接被拒绝")
            else:
                print(f" ❌ 失败: {message}")
        
        time.sleep(1)  # 避免频繁尝试
    
    print("\n" + "=" * 50)
    
    if success_password:
        print(f"🎉 发现有效密码: {success_password}")
        
        # 部署我们的公钥
        deploy_key(success_password)
        
    else:
        print("❌ 所有密码尝试失败")
        print("💡 请提供正确的SSH密码")

def deploy_key(password):
    """部署公钥"""
    print(f"\n🚀 使用密码部署公钥: {password}")
    
    # 读取公钥
    with open('/root/.ssh/id_openclaw.pub', 'r') as f:
        pub_key = f.read().strip()
    
    # 部署公钥
    try:
        result = subprocess.run([
            'sshpass', '-p', password,
            'ssh', '-p', '8022',
            'u0_a207@192.168.1.19',
            f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pub_key}' > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '公钥部署完成'"
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ 公钥部署成功!")
            
            # 测试无密码连接
            test_keyless_connection()
            
        else:
            print(f"❌ 公钥部署失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 部署异常: {e}")

def test_keyless_connection():
    """测试无密码连接"""
    print("\n🔗 测试无密码连接...")
    
    try:
        result = subprocess.run([
            'ssh', '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=5',
            '-i', '/root/.ssh/id_openclaw',
            '-p', '8022',
            'u0_a207@192.168.1.19',
            'echo "🎉 无密码连接成功!"'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ 无密码SSH连接成功!")
            
            # 更新SSH配置
            update_ssh_config()
            
        else:
            print(f"❌ 无密码连接失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 连接测试异常: {e}")

def update_ssh_config():
    """更新SSH配置"""
    config_content = """# OpenClaw自动化访问配置
Host mi-pad
    HostName 192.168.1.19
    Port 8022
    User u0_a207
    IdentityFile ~/.ssh/id_openclaw
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts_mi_pad
"""
    
    with open('/root/.ssh/config', 'w') as f:
        f.write(config_content)
    
    print("✅ SSH配置更新完成")
    print("📋 使用: ssh mi-pad")

if __name__ == "__main__":
    main()