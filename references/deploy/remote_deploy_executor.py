#!/usr/bin/env python3
"""
远程Windows部署执行器
通过WinRM执行OpenClaw部署
"""

import subprocess
import sys
import time

def run_winrm_command(command, description, timeout=30):
    """尝试通过WinRM执行命令"""
    print(f"🚀 {description}")
    print(f"命令: {command}")
    
    try:
        # 使用sshpass通过WinRM端口执行命令
        # 注意：WinRM使用5985端口，但需要正确的协议
        cmd = f"sshpass -p 'c9fc9f,.' ssh -o StrictHostKeyChecking=no -p 5985 administrator@192.168.2.134 '{command}'"
        
        result = subprocess.run(
            cmd, shell=True, 
            capture_output=True, text=True, timeout=timeout
        )
        
        if result.returncode == 0:
            print("✅ 执行成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"❌ 执行失败 (代码: {result.returncode})")
            if result.stderr.strip():
                print(f"错误: {result.stderr.strip()}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print("⏰ 命令执行超时")
        return False, "timeout"
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False, str(e)

def deploy_openclaw():
    """执行OpenClaw部署"""
    print("🎯 开始远程OpenClaw部署")
    print("=" * 50)
    print("目标: administrator@192.168.2.134:5985")
    print("=" * 50)
    
    # 1. 测试连接
    success, output = run_winrm_command("echo Connected successfully", "测试连接")
    if not success:
        print("❌ 连接测试失败，无法继续部署")
        return False
    
    # 2. 检查Node.js
    print("\\n🔍 检查Node.js...")
    success, output = run_winrm_command("node --version", "检查Node.js")
    
    if not success:
        print("❌ Node.js未安装")
        print("💡 需要在目标设备上手动安装Node.js")
        
        # 提供安装指导
        print("\\n📋 安装Node.js步骤:")
        print("1. 访问 https://nodejs.org")
        print("2. 下载Windows安装包")
        print("3. 运行安装程序")
        print("4. 重新打开命令提示符")
        print("5. 验证: node --version")
        
        return False
    
    # 3. 安装OpenClaw
    print("\\n📦 安装OpenClaw...")
    success, output = run_winrm_command("npm install -g openclaw@latest", "安装OpenClaw", timeout=120)
    
    if not success:
        print("❌ OpenClaw安装失败")
        return False
    
    # 4. 初始化配置
    print("\\n⚙️  初始化配置...")
    success, output = run_winrm_command(
        "if not exist \"%USERPROFILE%\\.openclaw\" mkdir \"%USERPROFILE%\\.openclaw\" && openclaw setup", 
        "初始化配置", timeout=60
    )
    
    # 5. 启动服务
    print("\\n🚀 启动服务...")
    success, output = run_winrm_command(
        "taskkill /f /im node.exe /fi \"windowtitle eq openclaw*\" 2>nul && start \"OpenClaw Gateway\" /B node -e \"require('openclaw').startGateway({port: 18789})\"",
        "启动服务", timeout=30
    )
    
    # 6. 验证部署
    print("\\n✅ 验证部署...")
    time.sleep(5)  # 等待服务启动
    
    success, output = run_winrm_command(
        "powershell -Command \"try { $response = Invoke-WebRequest -Uri 'http://localhost:18789/health' -Method Get -TimeoutSec 5; if ($response.StatusCode -eq 200) { $health = $response.Content | ConvertFrom-Json; if ($health.ok) { echo 'SUCCESS' } else { echo 'FAILED' } } else { echo 'HTTP_ERROR' } } catch { echo 'CONNECTION_ERROR' }\"",
        "健康检查", timeout=15
    )
    
    if success and 'SUCCESS' in output:
        print("🎉 部署成功! OpenClaw服务正常运行")
        print("📍 访问地址: http://192.168.2.134:18789")
        return True
    else:
        print("⚠️  部署完成，但服务验证失败")
        print("💡 请手动检查服务状态")
        return False

def main():
    """主函数"""
    print("准备执行远程Windows部署...")
    
    # 检查sshpass
    try:
        subprocess.run(["which", "sshpass"], capture_output=True, check=True)
    except:
        print("❌ sshpass未安装")
        print("请安装: sudo apt install sshpass")
        return False
    
    # 执行部署
    success = deploy_openclaw()
    
    print("\\n" + "=" * 50)
    if success:
        print("✅ 远程部署完成!")
    else:
        print("❌ 远程部署遇到问题")
        print("💡 建议使用手动部署方案")
    
    return success

if __name__ == "__main__":
    main()