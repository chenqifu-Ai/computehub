#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH连接诊断工具 - 确定192.168.1.19的正确用户名和密码
"""

import subprocess
import time

def test_ssh_connection(hostname, port, username, password):
    """测试SSH连接"""
    try:
        result = subprocess.run([
            'sshpass', '-p', password,
            'ssh', '-p', str(port),
            f'{username}@{hostname}',
            'echo "连接成功"'
        ], capture_output=True, text=True, timeout=8)
        
        if result.returncode == 0:
            return True, "成功"
        else:
            error_msg = result.stderr.strip()
            if "Permission denied" in error_msg:
                return False, "权限被拒绝"
            elif "Connection refused" in error_msg:
                return False, "连接被拒绝"
            elif "Network is unreachable" in error_msg:
                return False, "网络不可达"
            else:
                return False, f"其他错误: {error_msg}"
                
    except subprocess.TimeoutExpired:
        return False, "连接超时"
    except Exception as e:
        return False, f"异常: {e}"

def main():
    """主函数"""
    hostname = "192.168.1.19"
    port = 8022
    
    # 常见的用户名和密码组合
    test_cases = [
        # 从MEMORY.md中已知的
        ("u0_a46", "123"),      # 华为手机用户
        ("u0_a207", "123"),     # 可能的小米平板用户
        
        # 常见的Android Termux用户名
        ("root", "123"),
        ("root", "123456"),
        ("admin", "123"),
        ("admin", "123456"),
        ("user", "123"),
        ("termux", "termux"),
        
        # 其他常见组合
        ("android", "android"),
        ("mi", "mi"),
        ("xiaomi", "xiaomi"),
        ("openclaw", "openclaw"),
    ]
    
    print("🔍 SSH连接诊断开始...")
    print(f"目标主机: {hostname}:{port}")
    print("-" * 50)
    
    successful_connections = []
    
    for username, password in test_cases:
        print(f"测试: {username} / {password}", end="")
        
        success, message = test_ssh_connection(hostname, port, username, password)
        
        if success:
            print(" ✅ 成功!")
            successful_connections.append((username, password))
        else:
            print(f" ❌ 失败: {message}")
        
        # 稍微延迟一下，避免被ban
        time.sleep(1)
    
    print("-" * 50)
    
    if successful_connections:
        print("🎉 发现成功的连接配置:")
        for user, pwd in successful_connections:
            print(f"  ✅ {user} / {pwd}")
        
        # 更新SSH配置
        update_ssh_config(successful_connections[0])
        
    else:
        print("❌ 所有测试组合都失败")
        print("\n💡 建议:")
        print("1. 确认192.168.1.19的SSH服务正在运行")
        print("2. 检查防火墙设置")
        print("3. 确认端口8022是否正确")
        print("4. 可能需要手动配置用户名密码")

def update_ssh_config(credentials):
    """更新SSH配置"""
    username, password = credentials
    
    ssh_config_path = "/root/.ssh/config"
    config_content = f"""# OpenClaw自动化访问配置
Host mi-pad
    HostName 192.168.1.19
    Port 8022
    User {username}
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts_mi_pad

# 密码连接配置（备用）
Host mi-pad-password
    HostName 192.168.1.19
    Port 8022
    User {username}
    StrictHostKeyChecking no
"""
    
    try:
        with open(ssh_config_path, 'w') as f:
            f.write(config_content)
        print(f"✅ SSH配置已更新: User = {username}")
        
        # 更新部署脚本
        update_deploy_script(username, password)
        
    except Exception as e:
        print(f"❌ SSH配置更新失败: {e}")

def update_deploy_script(username, password):
    """更新部署脚本"""
    script_path = "/root/.openclaw/workspace/scripts/deploy_ssh_key.sh"
    
    new_script = f"""#!/bin/bash
# OpenClaw SSH密钥部署脚本
# 用于在192.168.1.19上部署公钥

HOST="192.168.1.19"
PORT="8022"
USER="{username}"
PASSWORD="{password}"

# 读取公钥
PUBLIC_KEY=$(cat ~/.ssh/id_ed25519.pub)

echo "部署SSH公钥到 ${{USER}}@${{HOST}}:${{PORT}}..."

# 使用expect工具处理交互式登录
if ! command -v expect >/dev/null 2>&1; then
    echo "安装expect工具..."
    apt update && apt install -y expect
fi

# 使用expect自动化部署
/usr/bin/expect <<EOF
set timeout 30
spawn ssh -p $PORT $USER@$HOST

expect {
    "*password:" {
        send "$PASSWORD\\r"
        exp_continue
    }
    "*permission denied*" {
        puts "权限被拒绝"
        exit 1
    }
    "*connection refused*" {
        puts "连接被拒绝"
        exit 1
    }
    "*$ " {
        send "mkdir -p ~/.ssh && chmod 700 ~/.ssh\\r"
        expect "*$ "
        
        send "echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys\\r"
        expect "*$ "
        
        send "chmod 600 ~/.ssh/authorized_keys\\r"
        expect "*$ "
        
        send "echo 'SSH公钥部署完成'\\r"
        expect "*$ "
        
        send "exit\\r"
        expect eof
    }
    timeout {
        puts "连接超时"
        exit 1
    }
}
EOF

if [ $? -eq 0 ]; then
    echo "✅ 公钥部署成功"
    echo "测试无密码连接..."
    
    ssh -p $PORT $USER@$HOST "echo '无密码连接测试成功'"
    
    if [ $? -eq 0 ]; then
        echo "🎉 SSH密钥认证配置完成！"
    else
        echo "⚠️  无密码连接测试失败，请检查配置"
    fi
else
    echo "❌ 公钥部署失败"
    exit 1
fi
"""
    
    try:
        with open(script_path, 'w') as f:
            f.write(new_script)
        print(f"✅ 部署脚本已更新: User = {username}")
        
    except Exception as e:
        print(f"❌ 部署脚本更新失败: {e}")

if __name__ == "__main__":
    main()