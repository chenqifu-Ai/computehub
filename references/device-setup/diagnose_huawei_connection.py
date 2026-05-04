#!/usr/bin/env python3
"""
华为手机连接诊断脚本
根据MEMORY.md中的标准连接流程进行诊断
"""

import subprocess
import time

def run_command(cmd, description):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(f"✅ 成功: {description}")
            return True, result.stdout.strip()
        else:
            print(f"❌ 失败: {description}")
            print(f"错误: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ 超时: {description}")
        return False, "命令执行超时"
    except Exception as e:
        print(f"💥 异常: {description} - {str(e)}")
        return False, str(e)

def check_network_connectivity():
    """检查网络连通性"""
    print("\n🌐 检查网络连通性...")
    
    # Ping测试
    success, output = run_command("ping -c 3 192.168.1.9", "Ping测试")
    if not success:
        print("❌ 网络不通，请检查网络连接")
        return False
    
    # 端口扫描
    success, output = run_command("nc -zv 192.168.1.9 8022 2>&1 || echo '端口检查失败'", "检查SSH端口")
    port_open = "succeeded" in output or "open" in output
    
    print(f"📡 SSH端口状态: {'✅ 开放' if port_open else '❌ 关闭'}")
    return port_open

def check_ssh_service():
    """检查SSH服务状态"""
    print("\n🔌 检查SSH服务状态...")
    
    # 多种SSH连接测试
    tests = [
        ("ssh -p 8022 -o ConnectTimeout=5 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'echo test'", "SSH简单命令"),
        ("sshpass -p 123 ssh -p 8022 -o ConnectTimeout=5 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'echo test'", "SSH带密码连接"),
        ("timeout 5 ssh -p 8022 -v u0_a46@192.168.1.9 2>&1 | head -10", "SSH详细模式")
    ]
    
    for cmd, description in tests:
        success, output = run_command(cmd, description)
        if success:
            print(f"✅ SSH服务正常: {output}")
            return True
    
    print("❌ 所有SSH连接测试失败")
    return False

def check_termux_status():
    """检查Termux状态"""
    print("\n📱 检查Termux环境...")
    
    # 尝试通过其他方式检查Termux
    success, output = run_command("adb devices 2>/dev/null | grep 192.168.1.9 || echo 'ADB未连接'", "ADB设备检查")
    
    # 检查是否可以通过其他端口连接
    success, output = run_command("curl -s http://192.168.1.9:8080 2>/dev/null || echo 'HTTP服务检查'", "HTTP服务检查")
    
    return False  # 默认返回False，需要进一步诊断

def suggest_solutions():
    """提供解决方案建议"""
    print("\n💡 连接问题解决方案:")
    print("=" * 50)
    
    print("\n1. 📱 在华为手机上检查Termux:")
    print("   - 打开Termux应用")
    print("   - 运行: sshd")
    print("   - 检查SSH服务是否启动")
    print("   - 运行: netstat -tln | grep :8022")
    
    print("\n2. 🔧 SSH服务配置检查:")
    print("   - 检查~/.ssh/sshd_config")
    print("   - 确认Port 8022")
    print("   - 检查防火墙设置")
    
    print("\n3. 🌐 网络配置检查:")
    print("   - 确认WiFi连接正常")
    print("   - 检查IP地址是否变化")
    print("   - 尝试重启网络服务")
    
    print("\n4. 🔄 重启服务:")
    print("   - 在Termux中: pkill sshd && sshd")
    print("   - 或者重启Termux应用")
    
    print("\n5. 📋 标准连接流程确认:")
    print("   ssh -p 8022 u0_a46@192.168.1.9")
    print("   输入密码: 123")
    print("   进入Ubuntu: proot-distro login ubuntu")

def main():
    """主函数"""
    print("=" * 60)
    print("📱 华为手机连接诊断工具")
    print("📡 目标设备: 192.168.1.9 (华为手机)")
    print("=" * 60)
    
    # 检查网络连通性
    network_ok = check_network_connectivity()
    if not network_ok:
        print("\n❌ 网络连接问题，请先解决网络连通性")
        suggest_solutions()
        return False
    
    # 检查SSH服务
    ssh_ok = check_ssh_service()
    if not ssh_ok:
        print("\n❌ SSH服务问题，需要检查Termux配置")
        suggest_solutions()
        return False
    
    print("\n🎉 连接诊断完成，SSH服务正常")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ 需要手动检查华为手机上的Termux和SSH配置")
    else:
        print("\n✅ 可以正常连接华为手机")