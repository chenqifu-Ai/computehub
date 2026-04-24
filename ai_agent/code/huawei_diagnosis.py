#!/usr/bin/env python3
"""
华为手机OpenClaw状态诊断脚本
按照AI智能体SOP流程执行完整诊断
"""

import subprocess
import sys
import time
from datetime import datetime

def run_command(cmd, description=""):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    print(f"  命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"  返回码: {result.returncode}")
        if result.stdout:
            print(f"  输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"  错误: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("  ⚠️ 命令执行超时")
        return False, "", "Timeout"
    except Exception as e:
        print(f"  ❌ 执行异常: {e}")
        return False, "", str(e)

def main():
    print("🤖 开始华为手机OpenClaw状态诊断")
    print("=" * 50)
    
    # 设备信息
    host = "192.168.1.9"
    port = "8022"
    user = "u0_a46"
    password = "123"
    
    # 步骤1: 网络连通性测试
    print("\n1️⃣ 网络连通性测试")
    success, stdout, stderr = run_command(
        f"ping -c 3 {host}",
        "Ping测试网络连通性"
    )
    
    if not success:
        print("❌ 网络连接失败，无法继续诊断")
        return False
    
    # 步骤2: SSH端口扫描
    print("\n2️⃣ SSH端口状态检查")
    success, stdout, stderr = run_command(
        f"nc -zv {host} {port} -w 3",
        "检查SSH端口8022状态"
    )
    
    # 步骤3: 尝试其他端口
    print("\n3️⃣ 其他可能端口检查")
    ports_to_check = ["5555", "18789", "22"]
    for port_num in ports_to_check:
        success, stdout, stderr = run_command(
            f"nc -zv {host} {port_num} -w 2",
            f"检查端口 {port_num}"
        )
    
    # 步骤4: ADB连接测试
    print("\n4️⃣ ADB连接测试")
    success, stdout, stderr = run_command(
        f"adb connect {host}:5555",
        "尝试ADB连接"
    )
    
    # 步骤5: 详细网络诊断
    print("\n5️⃣ 详细网络诊断")
    run_command(
        f"nmap -p 8022,18789,5555,22 {host}",
        "端口扫描详细结果"
    )
    
    # 步骤6: 尝试其他连接方式
    print("\n6️⃣ 替代连接方式测试")
    
    # 尝试直接telnet
    run_command(
        f"echo 'exit' | timeout 5 telnet {host} {port}",
        "Telnet连接测试"
    )
    
    # 步骤7: 生成诊断报告
    print("\n7️⃣ 生成诊断报告")
    report = f"""
📋 华为手机OpenClaw诊断报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
设备: {host} (华为手机 HWI-AL00)

诊断结果:
- 网络连通性: {'✅ 正常' if success else '❌ 异常'}
- SSH端口8022: {'✅ 开放' if 'succeeded' in stdout else '❌ 关闭'}
- 建议下一步操作:
"""
    
    print(report)
    
    # 保存报告
    with open(f"/root/.openclaw/workspace/ai_agent/results/huawei_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
        f.write(report)
    
    print("✅ 诊断完成，报告已保存")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)