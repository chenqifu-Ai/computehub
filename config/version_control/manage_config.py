#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置版本控制 - 统一管理入口
"""

import os
import sys
import subprocess

SCRIPTS_DIR = "/root/.openclaw/workspace/config/version_control"

def show_help():
    print("""
配置版本控制系统管理工具

用法:
  python manage_config.py snapshot [描述]     # 创建快照
  python manage_config.py rollback <快照ID>   # 回退到快照
  python manage_config.py list               # 列出所有快照
  python manage_config.py status             # 显示当前状态
  python manage_config.py help               # 显示帮助

示例:
  python manage_config.py snapshot "更新邮箱配置"
  python manage_config.py rollback snapshot_2026-03-26T18-27-11-320545
  python manage_config.py list
""")

def run_script(script_name, args=None):
    """运行指定脚本"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 执行脚本失败: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    remaining_args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    if command == "snapshot":
        description = " ".join(remaining_args) if remaining_args else "Manual snapshot"
        run_script("create_snapshot.py", [description])
    
    elif command == "rollback":
        if not remaining_args:
            print("❌ 请指定要回退的快照ID")
            print("使用 'python manage_config.py list' 查看可用快照")
            return
        snapshot_id = remaining_args[0]
        dry_run = '--dry-run' in remaining_args
        args = [snapshot_id]
        if dry_run:
            args.append('--dry-run')
        run_script("rollback_to_snapshot.py", args)
    
    elif command == "list":
        run_script("rollback_to_snapshot.py", [])
    
    elif command == "status":
        current_state_file = "/root/.openclaw/workspace/config/version_control/current_state.json"
        if os.path.exists(current_state_file):
            with open(current_state_file, 'r', encoding='utf-8') as f:
                import json
                state = json.load(f)
                print(f"📊 当前配置状态:")
                print(f"   最后更新: {state.get('timestamp', 'Unknown')}")
                print(f"   配置文件数: {len(state.get('files', {}))}")
                print(f"\n📁 配置文件列表:")
                for filename, info in state.get('files', {}).items():
                    print(f"   - {filename} (大小: {info.get('size', 0)} 字节)")
        else:
            print("❌ 没有找到当前状态文件，请先创建快照")
    
    elif command == "help":
        show_help()
    
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()