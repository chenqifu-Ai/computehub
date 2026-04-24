#!/usr/bin/env python3
"""
Gateway服务诊断脚本
"""

import subprocess
import sys

def run_ssh_command(cmd):
    """执行SSH命令"""
    ssh_cmd = f"sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a46@10.35.204.26 '{cmd}'"
    try:
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", f"执行错误: {e}"

def diagnose():
    """诊断Gateway问题"""
    print("🔧 开始诊断Gateway服务问题")
    print("=" * 50)
    
    # 1. 检查OpenClaw安装
    success, stdout, stderr = run_ssh_command("openclaw --version")
    if success:
        print("✅ OpenClaw安装正常:", stdout.strip())
    else:
        print("❌ OpenClaw安装问题:", stderr)
        return False
    
    # 2. 检查配置文件
    success, stdout, stderr = run_ssh_command("ls -la ~/.openclaw/openclaw.json")
    if success:
        print("✅ 配置文件存在")
    else:
        print("❌ 配置文件缺失")
        return False
    
    # 3. 检查端口占用
    success, stdout, stderr = run_ssh_command("netstat -tln 2>/dev/null | grep :18789 || echo '端口空闲'")
    if "端口空闲" in stdout:
        print("✅ 端口18789空闲")
    else:
        print("⚠️  端口可能被占用:", stdout.strip())
    
    # 4. 尝试启动Gateway
    print("🚀 尝试启动Gateway...")
    success, stdout, stderr = run_ssh_command("timeout 5 openclaw gateway --port 18789")
    
    if success:
        print("✅ Gateway启动成功")
        print("输出:", stdout)
    else:
        print("❌ Gateway启动失败")
        print("错误:", stderr)
        
        # 检查详细错误
        success, stdout, stderr = run_ssh_command("openclaw gateway --port 18789 --verbose 2>>1 | head -10")
        print("详细错误:", stderr or stdout)
    
    # 5. 检查系统日志
    success, stdout, stderr = run_ssh_command("dmesg | tail -5 2>/dev/null || logcat -d | tail -5 2>/dev/null || echo '无系统日志'")
    print("系统日志:", stdout.strip())
    
    print("=" * 50)
    return success

def main():
    success = diagnose()
    if success:
        print("🎉 诊断完成 - Gateway应该正常工作")
    else:
        print("⚠️  诊断完成 - 发现问题需要修复")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())