#!/usr/bin/env python3
"""
华为手机OpenClaw恢复脚本
基于诊断结果执行恢复操作
"""

import subprocess
import sys
from datetime import datetime

def run_command(cmd, description=""):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    print(f"  命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
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
    print("🤖 开始华为手机OpenClaw恢复操作")
    print("=" * 50)
    
    # 设备信息
    host = "192.168.1.9"
    port = "8022"
    user = "u0_a46"
    password = "123"
    gateway_port = "18789"
    
    # 方案1: 使用装机技能重新部署
    print("\n1️⃣ 方案一: 使用装机技能重新部署")
    
    deploy_script = "/root/.openclaw/workspace/skills/zhuangji-skill/deploy.sh"
    
    # 检查装机脚本是否存在
    check_cmd = f"test -f {deploy_script} && echo '存在' || echo '不存在'"
    exists, stdout, stderr = run_command(check_cmd, "检查装机脚本")
    
    if "存在" in stdout:
        print("✅ 装机脚本存在，开始部署...")
        
        # 执行部署
        deploy_cmd = f"cd /root/.openclaw/workspace/skills/zhuangji-skill && ./deploy.sh {host} {port} {user} {password} {gateway_port}"
        success, stdout, stderr = run_command(deploy_cmd, "执行装机部署")
        
        if success:
            print("✅ 部署成功！")
            return True
        else:
            print("❌ 部署失败，尝试方案二")
    else:
        print("❌ 装机脚本不存在，尝试方案二")
    
    # 方案2: 手动恢复步骤
    print("\n2️⃣ 方案二: 手动恢复步骤")
    
    # 步骤1: 检查设备是否可访问
    print("\n📱 步骤1: 检查设备基础访问")
    
    # 尝试通过其他方式连接
    run_command(f"ping -c 2 {host}", "再次确认网络连通性")
    
    # 步骤2: 检查Termux环境
    print("\n📱 步骤2: 检查Android Termux环境")
    
    # 尝试ADB调试
    run_command("adb devices", "检查ADB设备")
    
    # 步骤3: 建议手动操作
    print("\n📱 步骤3: 需要手动操作建议")
    
    manual_steps = """
请手动在华为手机上执行以下操作:

1. 打开Termux应用
2. 检查OpenClaw服务状态:
   openclaw gateway status

3. 如果服务停止，启动服务:
   openclaw gateway start

4. 检查端口监听:
   netstat -tlnp | grep 8022
   netstat -tlnp | grep 18789

5. 如果问题依旧，尝试重启Termux或手机
"""
    
    print(manual_steps)
    
    # 生成恢复报告
    report = f"""
📋 华为手机OpenClaw恢复报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
设备: {host} (华为手机 HWI-AL00)

执行结果:
- 装机技能部署: {'✅ 成功' if success else '❌ 失败或未尝试'}
- 当前状态: 需要手动干预

手动操作步骤已提供，请按照建议在手机上操作。
"""
    
    print(report)
    
    # 保存报告
    with open(f"/root/.openclaw/workspace/ai_agent/results/huawei_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
        f.write(report)
    
    print("✅ 恢复操作完成，请按照手动步骤操作")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)