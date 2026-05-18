#!/usr/bin/env python3
"""
Computehub 进程诊断与清理脚本
目标: 远程 SSH 到 36.250.122.43，诊断重复 gateway 进程并清理
"""

import subprocess
import json
import sys
from datetime import datetime

SSH_USER = "computehub"
SSH_HOST = "36.250.122.43"
SSH_KEY = "/root/.ssh/id_ed25519_computehub"
SSH_OPTS = f"-o StrictHostKeyChecking=no -o ConnectTimeout=10"

def run_ssh(command, timeout=30):
    """通过 SSH 执行远程命令"""
    full_cmd = f'ssh {SSH_OPTS} -i {SSH_KEY} {SSH_USER}@{SSH_HOST} "{command}"'
    try:
        result = subprocess.run(
            full_cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "SSH timeout", -1
    except Exception as e:
        return "", str(e), -1

def diagnose():
    """诊断当前进程状态"""
    print("=" * 60)
    print(f"📡 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 查看所有 computehub 进程
    cmd = 'ps aux | grep computehub | grep -v grep'
    stdout, stderr, rc = run_ssh(cmd)
    print("\n🔍 当前 computehub 进程:")
    print("-" * 60)
    if stdout:
        for line in stdout.split("\n"):
            print(f"  {line}")
    else:
        print("  ❌ 命令执行失败")
    
    # 2. 查看端口占用
    cmd2 = 'ss -tlnp | grep -E "8282|22"'
    stdout2, stderr2, rc2 = run_ssh(cmd2)
    print("\n🔌 端口占用:")
    print("-" * 60)
    if stdout2:
        print(stdout2)
    else:
        print("  无法获取端口信息")
    
    # 3. 查看 Gateway 状态
    cmd3 = 'curl -s http://localhost:8282/api/health 2>/dev/null || echo "Gateway 不可达"'
    stdout3, stderr3, rc3 = run_ssh(cmd3)
    print("\n🏥 Gateway 健康检查:")
    print("-" * 60)
    print(f"  {stdout3}")
    
    # 4. 查看进程树
    cmd4 = 'ps auxf | grep computehub | head -50'
    stdout4, stderr4, rc4 = run_ssh(cmd4)
    print("\n🌳 进程树:")
    print("-" * 60)
    if stdout4:
        for line in stdout4.split("\n"):
            print(f"  {line}")
    
    # 5. 查看日志
    cmd5 = 'tail -20 /tmp/gateway.log 2>/dev/null || echo "无 gateway 日志"'
    stdout5, stderr5, rc5 = run_ssh(cmd5)
    print("\n📋 最近 gateway 日志:")
    print("-" * 60)
    print(stdout5)

def cleanup():
    """安全清理所有 computehub 进程并重启"""
    print("\n" + "=" * 60)
    print("🧹 开始清理...")
    print("=" * 60)
    
    # 步骤1: 保存健康检查状态
    cmd_health = 'curl -s http://localhost:8282/api/health 2>/dev/null'
    stdout, _, _ = run_ssh(cmd_health)
    print(f"📊 重启前健康状态: {stdout}")
    
    # 步骤2: 杀掉所有 computehub 进程
    cmd_kill = 'pkill -f computehub; sleep 2; ps aux | grep computehub | grep -v grep || echo "所有进程已清理"'
    stdout, stderr, rc = run_ssh(cmd_kill)
    print(f"🗑️  清理结果: {stdout}")
    
    if stderr and "timeout" in stderr.lower():
        print("  ⚠️  SSH 超时，可能部分进程未清理")
        # 再次确认
        check = 'ps aux | grep computehub | grep -v grep'
        _, _, _ = run_ssh(check)
    
    sleep(3)
    
    # 步骤3: 确认清理完成
    check = 'ps aux | grep computehub | grep -v grep || echo "✅ 确认无 computehub 进程"'
    stdout, _, _ = run_ssh(check)
    print(f"\n✅ 清理确认: {stdout}")
    
    # 步骤4: 重启 Gateway（假设使用 v0.7.9）
    # 先检查 v0.7.9 是否存在
    check_v79 = 'ls -la ~/computehub-v0.7.9 2>/dev/null && echo "v0.7.9存在" || echo "v0.7.9不存在"'
    stdout, _, _ = run_ssh(check_v79)
    print(f"\n📦 版本检查: {stdout}")
    
    # 确定要用的二进制
    binary = "~/computehub-v0.7.9"
    version_check = 'test -x ~/computehub-v0.7.9 && echo "v0.7.9" || (test -x ~/computehub-v0.7.8 && echo "v0.7.8" || echo "none")'
    ver_stdout, _, _ = run_ssh(version_check)
    
    if ver_stdout == "v0.7.9":
        binary = "~/computehub-v0.7.9"
        print("🎯 使用 v0.7.9 重启")
    elif ver_stdout == "v0.7.8":
        binary = "~/computehub-v0.7.8"
        print("⚠️  降级到 v0.7.8（v0.7.9 不可用）")
    else:
        print("❌ 找不到可执行文件！")
        return False
    
    # 步骤5: 启动 Gateway
    gw_cmd = f'nohup {binary} gateway --port 8282 --config config.json > /tmp/gateway.log 2>&1 &'
    stdout, stderr, rc = run_ssh(gw_cmd)
    print(f"\n🚀 启动 Gateway: {stdout or '(后台启动)'}")
    
    sleep(5)
    
    # 步骤6: 验证启动
    health = 'curl -s http://localhost:8282/api/health 2>/dev/null || echo "Gateway 不可达"'
    stdout, _, _ = run_ssh(health)
    print(f"✅ 健康检查: {stdout}")
    
    # 步骤7: 最终进程检查
    final_check = 'ps aux | grep computehub | grep -v grep | wc -l'
    stdout, _, _ = run_ssh(final_check)
    count = stdout.strip()
    print(f"\n📊 最终进程数: {count}")
    
    if int(count) <= 3:  # parent + gateway + worker + optional
        print("✅ 清理成功！进程数正常")
        return True
    else:
        print(f"❌ 仍有 {count} 个进程，可能还有问题")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup()
    else:
        diagnose()
