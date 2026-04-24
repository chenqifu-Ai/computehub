#!/usr/bin/env python3
"""
远程Windows部署执行器
通过WinRM执行OpenClaw部署到192.168.2.134
"""

import subprocess
import sys
import time

def run_ssh_command(command, description):
    """执行SSH命令到Windows设备"""
    print(f"🚀 {description}")
    print(f"命令: {command}")
    
    try:
        # 使用sshpass执行命令
        result = subprocess.run(
            f"sshpass -p 'c9fc9f,.' ssh -o StrictHostKeyChecking=no -p 5985 administrator@192.168.2.134 '{command}'",
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print("✅ 执行成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 执行失败 (代码: {result.returncode})")
            if result.stderr.strip():
                print(f"错误: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False

def deploy_openclaw():
    """执行OpenClaw部署流程"""
    print("🎯 开始OpenClaw Windows部署")
    print("=" * 60)
    print("目标设备: administrator@192.168.2.134:5985")
    print("=" * 60)
    
    # 1. 检查Node.js
    if not run_ssh_command("node --version", "检查Node.js安装"):
        print("❌ Node.js未安装，需要先安装Node.js")
        return False
    
    # 2. 安装OpenClaw
    if not run_ssh_command("npm install -g openclaw@latest", "安装OpenClaw"):
        print("❌ OpenClaw安装失败")
        return False
    
    # 3. 初始化配置
    if not run_ssh_command(
        "if not exist \"%USERPROFILE%\.openclaw\" mkdir \"%USERPROFILE%\.openclaw\" && openclaw setup", 
        "初始化配置"
    ):
        print("⚠️  配置初始化可能有警告，继续执行")
    
    # 4. 创建部署脚本
    deploy_script = '''
@echo off
chcp 65001 > nul
echo 启动OpenClaw Gateway服务...
taskkill /f /im node.exe /fi "windowtitle eq openclaw*" 2>nul
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18789})"
echo 等待服务启动...
timeout /t 5
echo 验证服务状态...
powershell -Command "try { $health = Invoke-RestMethod -Uri 'http://localhost:18789/health' -Method Get; if ($health.ok) { echo '✅ 服务正常运行' } else { echo '❌ 服务异常' } } catch { echo '❌ 服务检查失败' }"
echo.
echo OpenClaw部署完成!
echo Gateway: http://localhost:18789
pause
'''
    
    # 保存脚本到远程
    script_command = f"echo '{deploy_script}' > %TEMP%\\deploy_openclaw.bat"
    if not run_ssh_command(script_command, "创建部署脚本"):
        print("❌ 脚本创建失败")
        return False
    
    # 5. 执行部署脚本
    if not run_ssh_command("call %TEMP%\\deploy_openclaw.bat", "执行部署"):
        print("⚠️  部署执行可能有警告")
    
    # 6. 验证服务
    print("🔍 验证服务状态...")
    time.sleep(3)
    
    # 测试健康检查
    health_check = '''
try {
    $response = Invoke-WebRequest -Uri "http://localhost:18789/health" -Method Get -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $health = $response.Content | ConvertFrom-Json
        if ($health.ok) { 
            Write-Host "✅ HEALTH_CHECK_OK" 
            exit 0
        } else { 
            Write-Host "❌ HEALTH_CHECK_FAILED" 
            exit 1
        }
    } else {
        Write-Host "❌ HTTP_${$response.StatusCode}"
        exit 1
    }
} catch {
    Write-Host "❌ CONNECTION_ERROR: $($_.Exception.Message)"
    exit 1
}
'''
    
    if run_ssh_command(f"powershell -Command \"{health_check}\"", "健康检查"):
        print("🎉 OpenClaw部署成功!")
        print("📍 访问地址: http://192.168.2.134:18789")
        return True
    else:
        print("⚠️  部署完成但服务验证失败")
        print("💡 请手动检查服务状态")
        return False

def main():
    """主函数"""
    print("准备执行远程Windows部署...")
    
    # 检查sshpass是否可用
    try:
        subprocess.run(["which", "sshpass"], capture_output=True, check=True)
    except:
        print("❌ sshpass未安装，请先安装: apt install sshpass")
        return False
    
    # 执行部署
    success = deploy_openclaw()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 部署完成! OpenClaw服务已启动")
        print("📊 访问: http://192.168.2.134:18789/health")
    else:
        print("❌ 部署过程中遇到问题")
        print("💡 建议手动检查Windows设备状态")
    
    return success

if __name__ == "__main__":
    main()