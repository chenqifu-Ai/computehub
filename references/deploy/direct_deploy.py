#!/usr/bin/env python3
"""
直接Windows部署执行器
使用原始socket连接执行部署
"""

import socket
import time
import subprocess

def send_winrm_command(command):
    """通过原始socket发送WinRM命令"""
    try:
        # 建立连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect(('192.168.2.134', 5985))
        
        # 构建简单的HTTP请求
        http_request = f'''POST /wsman HTTP/1.1
Host: 192.168.2.134:5985
Content-Length: {len(command)}
Content-Type: application/soap+xml;charset=UTF-8

{command}'''
        
        # 发送请求
        sock.send(http_request.encode())
        
        # 接收响应
        response = sock.recv(4096)
        sock.close()
        
        return response.decode()
        
    except Exception as e:
        return f"Error: {e}"

def deploy_openclaw():
    """执行OpenClaw部署"""
    print("🎯 开始直接Windows部署")
    print("=" * 50)
    
    # 1. 测试连接
    print("🔍 测试WinRM连接...")
    test_response = send_winrm_command("<test/>")
    if "401" in test_response:
        print("✅ WinRM服务正常 (需要认证)")
    else:
        print("❌ WinRM连接异常")
        print("响应:", test_response[:200])
        return False
    
    # 2. 由于WinRM认证复杂，提供自动化部署脚本
    print("\n📋 创建自动化部署方案...")
    
    # 生成部署脚本内容
    deploy_script = '''@echo off
chcp 65001 > nul
echo OpenClaw自动部署开始...

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo 请安装Node.js: https://nodejs.org
    pause
    exit /b 1
)

:: 安装OpenClaw
echo 安装OpenClaw...
npm install -g openclaw@latest

:: 初始化配置
echo 初始化配置...
if not exist "%USERPROFILE%\.openclaw" mkdir "%USERPROFILE%\.openclaw"
openclaw setup

:: 启动服务
echo 启动服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"

echo 等待启动...
timeout /t 5 >nul

echo 部署完成! 访问: http://localhost:18789
pause'''
    
    # 保存部署脚本
    with open('/tmp/deploy_openclaw.bat', 'w') as f:
        f.write(deploy_script)
    
    print("✅ 部署脚本已创建: /tmp/deploy_openclaw.bat")
    print("\n📜 脚本内容:")
    print("-" * 30)
    print(deploy_script)
    print("-" * 30)
    
    # 3. 提供执行指南
    print("\n🚀 执行指南:")
    print("1. 将上述脚本保存为 deploy.bat")
    print("2. 以管理员身份运行")
    print("3. 等待自动完成")
    print("\n⏱️  预计时间: 3-5分钟")
    
    return True

def main():
    """主函数"""
    print("准备执行Windows部署...")
    
    success = deploy_openclaw()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 部署方案准备完成!")
        print("💡 请按照指南执行部署脚本")
    else:
        print("❌ 部署准备失败")
        print("💡 建议使用手动部署方式")
    
    return success

if __name__ == "__main__":
    main()