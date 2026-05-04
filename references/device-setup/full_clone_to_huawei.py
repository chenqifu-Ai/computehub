#!/usr/bin/env python3
"""
完整OpenClaw环境克隆脚本
将本机完整OpenClaw环境复制到华为手机
"""

import subprocess
import os
import time
from datetime import datetime

def run_command(cmd, description):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
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

def backup_target_device():
    """备份目标设备现有配置"""
    print("\n📦 备份目标设备配置...")
    
    backup_cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '"
    backup_cmd += "cd ~ && tar -czf openclaw_backup_$(date +%Y%m%d_%H%M).tar.gz .openclaw/ 2>/dev/null || echo \"无.openclaw目录\"'
    
    success, output = run_command(backup_cmd, "创建备份")
    return success

def sync_full_openclaw():
    """同步完整OpenClaw环境"""
    print("\n🔄 同步完整OpenClaw环境...")
    
    # 同步主配置目录
    sync_cmd = "cd /root/.openclaw && tar -czf - . | "
    sync_cmd += "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '"
    sync_cmd += "mkdir -p ~/.openclaw && cd ~/.openclaw && tar -xzf -'
    
    success, output = run_command(sync_cmd, "同步.openclaw目录")
    return success

def sync_workspace():
    """同步workspace目录"""
    print("\n💼 同步workspace内容...")
    
    # 同步workspace目录
    sync_cmd = "cd /root/.openclaw/workspace && tar -czf - . | "
    sync_cmd += "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '"
    sync_cmd += "mkdir -p ~/.openclaw/workspace && cd ~/.openclaw/workspace && tar -xzf -'
    
    success, output = run_command(sync_cmd, "同步workspace")
    return success

def sync_extensions():
    """同步extensions目录"""
    print("\n🔌 同步extensions...")
    
    # 同步extensions目录
    sync_cmd = "cd /root/.openclaw/extensions && tar -czf - . | "
    sync_cmd += "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '"
    sync_cmd += "mkdir -p ~/.openclaw/extensions && cd ~/.openclaw/extensions && tar -xzf -'
    
    success, output = run_command(sync_cmd, "同步extensions")
    return success

def verify_sync():
    """验证同步结果"""
    print("\n🔍 验证同步结果...")
    
    checks = [
        ("ls -la ~/.openclaw/ | wc -l", "检查.openclaw目录"),
        ("ls -la ~/.openclaw/workspace/ | wc -l", "检查workspace目录"),
        ("ls -la ~/.openclaw/extensions/ | wc -l", "检查extensions目录"),
        ("cat ~/.openclaw/openclaw.json | grep -c gateway", "检查配置文件"),
        ("find ~/.openclaw/workspace -name '*.py' | wc -l", "检查Python文件")
    ]
    
    results = []
    for cmd, description in checks:
        full_cmd = f"sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '{cmd}'"
        success, output = run_command(full_cmd, description)
        results.append((description, success, output))
    
    return results

def start_gateway():
    """启动Gateway服务"""
    print("\n🚀 启动Gateway服务...")
    
    # 停止现有服务
    stop_cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '"
    stop_cmd += "pkill -f openclaw 2>/dev/null || true'
    run_command(stop_cmd, "停止现有服务")
    
    time.sleep(2)
    
    # 启动Gateway
    start_cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '"
    start_cmd += "nohup openclaw gateway --no-daemon --allow-unconfigured > gateway.out 2> gateway.err &'
    
    success, output = run_command(start_cmd, "启动Gateway")
    
    time.sleep(3)
    
    # 检查服务状态
    check_cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '"
    check_cmd += "ps aux | grep openclaw | grep -v grep || echo \"无进程\"'
    
    success2, output2 = run_command(check_cmd, "检查服务状态")
    
    return success and success2, output2

def main():
    """主函数"""
    print("=" * 60)
    print("🦞 完整OpenClaw环境克隆")
    print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📡 源设备: 本机 (小龙虾)")
    print("📱 目标设备: 192.168.1.9 (华为手机)")
    print("=" * 60)
    
    # 执行完整克隆
    backup_success = backup_target_device()
    openclaw_success = sync_full_openclaw()
    workspace_success = sync_workspace()
    extensions_success = sync_extensions()
    
    # 验证同步
    verify_results = verify_sync()
    
    # 启动服务
    gateway_success, gateway_status = start_gateway()
    
    print("\n" + "=" * 60)
    print("📊 克隆完成报告")
    print("=" * 60)
    
    print(f"\n✅ 完成项目:")
    print(f"   配置备份: {'✅ 成功' if backup_success else '❌ 失败'}")
    print(f"   OpenClaw目录: {'✅ 成功' if openclaw_success else '❌ 失败'}")
    print(f"   Workspace: {'✅ 成功' if workspace_success else '❌ 失败'}")
    print(f"   Extensions: {'✅ 成功' if extensions_success else '❌ 失败'}")
    print(f"   Gateway服务: {'✅ 运行中' if gateway_success else '❌ 未运行'}")
    
    print(f"\n📋 同步验证:")
    for description, success, output in verify_results:
        status = "✅" if success else "❌"
        print(f"   {status} {description}: {output}")
    
    print(f"\n🌐 Gateway状态:")
    print(f"   {gateway_status}")
    
    if all([openclaw_success, workspace_success, extensions_success, gateway_success]):
        print("\n🎉 完整克隆成功！华为手机现在拥有与本机完全相同的OpenClaw环境")
    else:
        print("\n⚠️ 克隆部分成功，可能需要手动检查")

if __name__ == "__main__":
    main()