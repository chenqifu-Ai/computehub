#!/usr/bin/env python3
"""
通过WinRM在192.168.2.134上安装OpenClaw
"""

import subprocess
import sys

def run_winrm_command(command):
    """通过WinRM执行命令"""
    try:
        # 使用winrm命令执行
        cmd = [
            'winrm', 'invoke',
            '-username', 'chen',
            '-password', 'c9fc9f,.',
            '-hostname', '192.168.2.134',
            '-port', '5985',
            '-auth', 'basic',
            '-encoding', 'utf-8',
            'ExecuteCommand',
            '-arg:Command=' + command
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        return False, '', str(e)

def main():
    """主函数"""
    print("🚀 开始通过WinRM在192.168.2.134上安装OpenClaw")
    
    # 1. 测试连接
    print("\n1. 测试WinRM连接...")
    success, stdout, stderr = run_winrm_command("echo 'WinRM连接测试成功'")
    
    if success:
        print("✅ WinRM连接成功")
        print("输出:", stdout)
    else:
        print("❌ WinRM连接失败")
        print("错误:", stderr)
        return
    
    # 2. 检查系统信息
    print("\n2. 检查系统信息...")
    success, stdout, stderr = run_winrm_command("systeminfo | findstr /B /C:\"OS Name\" /C:\"OS Version\"")
    if success:
        print("✅ 系统信息:")
        print(stdout)
    
    # 3. 安装OpenClaw（简化版）
    print("\n3. 安装OpenClaw...")
    
    # 先检查是否已安装Node.js
    success, stdout, stderr = run_winrm_command("node --version")
    if not success:
        print("❌ Node.js未安装，需要先安装Node.js")
        print("请先在目标设备上安装Node.js，然后再运行此脚本")
        return
    
    print("✅ Node.js已安装:", stdout.strip())
    
    # 安装OpenClaw
    install_commands = [
        "npm install -g openclaw",
        "mkdir -p ~/.openclaw/workspace",
        "echo 'OpenClaw安装完成'"
    ]
    
    for cmd in install_commands:
        print(f"执行: {cmd}")
        success, stdout, stderr = run_winrm_command(cmd)
        if success:
            print("✅ 成功")
            if stdout:
                print("输出:", stdout)
        else:
            print("❌ 失败:", stderr)
            return
    
    print("\n🎉 OpenClaw安装完成！")
    print("接下来可以配置OpenClaw服务")

if __name__ == "__main__":
    main()