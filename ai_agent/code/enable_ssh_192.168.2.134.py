#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH服务启用脚本 - 192.168.2.134
目标：在目标设备启用SSH服务
"""

import subprocess
import sys
from pathlib import Path

def generate_ssh_setup_script():
    """生成SSH服务设置脚本"""
    script_content = """#!/bin/bash
# SSH服务自动设置脚本 - 192.168.2.134

echo "🚀 开始设置SSH服务..."

# 1. 更新系统
echo "📦 更新系统包..."
sudo apt update

# 2. 安装SSH服务器
echo "🔧 安装OpenSSH服务器..."
sudo apt install -y openssh-server

# 3. 启用并启动SSH服务
echo "⚡ 启用SSH服务..."
sudo systemctl enable ssh
sudo systemctl start ssh

# 4. 配置防火墙
echo "🛡️  配置防火墙允许SSH..."
sudo ufw allow ssh

# 5. 检查服务状态
echo "📊 检查SSH服务状态..."
sudo systemctl status ssh --no-pager

# 6. 验证SSH连接
echo "🔍 验证SSH连接..."
if command -v ssh &> /dev/null; then
    echo "✅ SSH客户端可用"
    echo "📝 连接命令: ssh chen@192.168.2.134"
else
    echo "❌ SSH客户端未安装，请安装: sudo apt install openssh-client"
fi

echo ""
echo "🎉 SSH服务设置完成!"
echo "💡 现在可以使用: ssh chen@192.168.2.134"
echo "🔑 密码: c9fc9f,."
"""
    
    script_path = Path("/tmp/enable_ssh.sh")
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    
    return script_path

def generate_ssh_test_script():
    """生成SSH连接测试脚本"""
    script_content = """#!/bin/bash
# SSH连接测试脚本 - 192.168.2.134

echo "🔍 测试SSH连接到 192.168.2.134..."

# 测试连接
echo "🧪 尝试连接..."
if ssh -o ConnectTimeout=10 -o BatchMode=no chen@192.168.2.134 "echo 'SSH连接成功!'"; then
    echo "✅ SSH连接测试成功!"
    echo ""
    echo "🎉 现在可以正常使用SSH:"
    echo "ssh chen@192.168.2.134"
else
    echo "❌ SSH连接失败"
    echo ""
    echo "可能的原因:"
    echo "1. SSH服务未启动"
    echo "2. 防火墙阻止"
    echo "3. 网络不可达"
    echo ""
    echo "💡 请先运行 enable_ssh.sh 设置脚本"
fi
"""
    
    script_path = Path("/tmp/test_ssh.sh")
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    
    return script_path

def generate_quick_commands():
    """生成快速命令参考"""
    commands = """# 🚀 SSH极速连接命令集

## 1. 设置SSH服务 (在目标设备运行)
sudo apt update && sudo apt install -y openssh-server
sudo systemctl enable ssh && sudo systemctl start ssh
sudo ufw allow ssh

## 2. 连接命令 (在当前设备运行)
ssh chen@192.168.2.134
# 密码: c9fc9f,.

## 3. 高级连接选项
ssh -o ConnectTimeout=10 chen@192.168.2.134  # 10秒超时
ssh -v chen@192.168.2.134                    # 详细模式
ssh -X chen@192.168.2.134                    # X11转发

## 4. 文件传输
scp localfile.txt chen@192.168.2.134:~/      # 上传文件
scp chen@192.168.2.134:~/remotefile.txt .    # 下载文件

## 5. 端口转发
ssh -L 8080:localhost:80 chen@192.168.2.134  # 本地端口转发
ssh -R 9090:localhost:90 chen@192.168.2.134  # 远程端口转发
"""
    
    commands_path = Path("/tmp/ssh_commands.txt")
    commands_path.write_text(commands)
    
    return commands_path

def main():
    """主函数"""
    print("🚀 SSH极速连接方案 - 192.168.2.134")
    print("=" * 60)
    
    # 生成脚本
    setup_script = generate_ssh_setup_script()
    test_script = generate_ssh_test_script()
    commands_file = generate_quick_commands()
    
    print("✅ 脚本生成完成:")
    print(f"   📜 SSH设置脚本: {setup_script}")
    print(f"   🧪 SSH测试脚本: {test_script}")
    print(f"   📋 命令参考: {commands_file}")
    
    print("\n" + "=" * 60)
    print("🎯 执行步骤:")
    print("1. 在目标设备 192.168.2.134 上运行:")
    print("   bash /tmp/enable_ssh.sh")
    print("2. 在当前设备测试连接:")
    print("   bash /tmp/test_ssh.sh")
    print("3. 开始使用SSH:")
    print("   ssh chen@192.168.2.134")
    
    print("\n" + "=" * 60)
    print("⚡ 极速命令 (复制执行):")
    print("# 目标设备上:")
    print("sudo apt update && sudo apt install -y openssh-server && sudo systemctl enable ssh && sudo systemctl start ssh && sudo ufw allow ssh")
    print("")
    print("# 当前设备测试:")
    print("ssh -o ConnectTimeout=10 chen@192.168.2.134 'echo ✅ SSH连接成功!'")

if __name__ == "__main__":
    main()