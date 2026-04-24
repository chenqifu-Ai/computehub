#!/usr/bin/env python3
"""
华为手机简单状态检查脚本
仅检查不进行任何修改操作
"""

import subprocess
import sys
from datetime import datetime

def run_command(cmd, description=""):
    """执行命令并返回结果"""
    print(f"🔍 {description}")
    print(f"  命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        print(f"  返回码: {result.returncode}")
        if result.stdout:
            print(f"  输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"  错误: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("  ⏰ 命令执行超时")
        return False, "", "Timeout"
    except Exception as e:
        print(f"  ❌ 执行异常: {e}")
        return False, "", str(e)

def main():
    print("🤖 华为手机状态检查（只读操作）")
    print("=" * 50)
    
    # 设备信息
    host = "192.168.1.9"
    
    # 只进行只读检查，不进行任何修改
    print("\n📊 只进行网络连通性检查")
    
    # 1. 基本ping测试
    success, stdout, stderr = run_command(
        f"ping -c 2 {host}",
        "网络连通性测试"
    )
    
    # 2. 端口状态检查（只读）
    print("\n📊 端口状态检查（只读）")
    ports = ["8022", "18789", "5555"]
    for port in ports:
        run_command(
            f"timeout 3 nc -zv {host} {port} || echo '端口 {port} 不可用'",
            f"检查端口 {port}"
        )
    
    # 生成只读报告
    report = f"""
📋 华为手机状态检查报告（只读）
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
设备: {host} (华为手机 HWI-AL00)

检查结果:
- 网络连通性: {'✅ 正常' if success else '❌ 异常'}
- 操作类型: 只读检查，无任何修改

建议:
请在华为手机上手动检查:
1. Termux应用是否运行
2. OpenClaw服务状态: openclaw gateway status
3. 如果需要重启: openclaw gateway restart
"""
    
    print(report)
    
    # 保存报告
    with open(f"/root/.openclaw/workspace/ai_agent/results/huawei_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
        f.write(report)
    
    print("✅ 只读检查完成，未进行任何修改操作")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)