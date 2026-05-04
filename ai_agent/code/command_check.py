#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令可用性检查脚本
"""

import subprocess
import os

def check_command(cmd):
    """检查命令是否可用"""
    try:
        result = subprocess.run(f"which {cmd}", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, None
    except:
        return False, None

def main():
    print("🔍 命令可用性检查")
    print("=" * 40)
    
    # 常用命令列表
    commands = [
        'openclaw', 'ssh', 'curl', 'ping', 'python',
        'node', 'npm', 'git', 'nano', 'vim',
        'sshd', 'netstat', 'ps', 'grep', 'find'
    ]
    
    available = []
    unavailable = []
    
    for cmd in commands:
        is_available, path = check_command(cmd)
        if is_available:
            available.append(f"{cmd} -> {path}")
        else:
            unavailable.append(cmd)
    
    print("✅ 可用的命令:")
    for cmd_info in available:
        print(f"   {cmd_info}")
    
    print("\n❌ 不可用的命令:")
    for cmd in unavailable:
        print(f"   {cmd}")
    
    print(f"\n📊 统计: {len(available)}/{len(commands)} 命令可用")
    
    # 检查PATH设置
    print(f"\n🌐 PATH环境变量:")
    path = os.environ.get('PATH', '')
    paths = path.split(':')
    for i, p in enumerate(paths[:10], 1):  # 显示前10个路径
        print(f"   {i:2d}. {p}")
    if len(paths) > 10:
        print(f"   ... 还有 {len(paths)-10} 个路径")

if __name__ == "__main__":
    main()