#!/usr/bin/env python3
"""
检查定时器脚本
查找可能限制 OpenClaw TUI 的定时任务
"""

import subprocess
import os

def check_timers():
    """检查所有定时任务"""
    
    print("🔍 开始检查定时任务...")
    
    # 1. 检查 crontab
    print("\n📋 检查 crontab:")
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'openclaw' in line.lower() or 'tui' in line.lower() or 'kill' in line.lower():
                    print(f"⚠️  发现可疑定时任务: {line}")
                elif line.strip() and not line.startswith('#'):
                    print(f"📅 正常定时任务: {line}")
        else:
            print("✅ 无 crontab 任务")
    except Exception as e:
        print(f"❌ 检查 crontab 失败: {e}")
    
    # 2. 检查 systemd 定时器
    print("\n⚙️  检查 systemd 定时器:")
    try:
        result = subprocess.run(['systemctl', 'list-timers', '--user'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'openclaw' in line.lower() or 'tui' in line.lower():
                    print(f"⚠️  发现可疑定时器: {line}")
    except Exception as e:
        print(f"❌ 检查 systemd 定时器失败: {e}")
    
    # 3. 检查进程监控脚本
    print("\n📁 检查进程监控脚本:")
    suspicious_files = []
    for root, dirs, files in os.walk('/home'):
        for file in files:
            if file.endswith('.sh') or file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read().lower()
                        if 'openclaw' in content and ('kill' in content or 'pkill' in content):
                            suspicious_files.append(filepath)
                            print(f"⚠️  发现可疑脚本: {filepath}")
                except:
                    pass
    
    if not suspicious_files:
        print("✅ 未发现可疑监控脚本")
    
    print("\n📊 检查完成")

if __name__ == "__main__":
    check_timers()