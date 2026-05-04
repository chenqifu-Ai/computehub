#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复多个项目中 ai_agent.py 文件导致的编辑失败问题
"""

import os
import shutil
from datetime import datetime

def create_backups():
    """为所有 ai_agent.py 文件创建备份"""
    files_to_backup = [
        '/root/.openclaw/workspace/framework/ai_agent.py',
        '/root/.openclaw/workspace/projects/chargecloud-opc/framework/ai_agent.py',
        '/root/.openclaw/workspace/projects/token_overseas/framework/ai_agent.py'
    ]
    
    backups = []
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{file_path}.backup_{timestamp}"
            shutil.copy2(file_path, backup_path)
            backups.append(backup_path)
            print(f"✅ 已创建备份: {backup_path}")
    return backups

def check_tui_config():
    """检查TUI客户端可能的配置文件"""
    config_locations = [
        '/root/.openclaw/tui-config.json',
        '/root/.openclaw/config/tui.json',
        '/root/.openclaw/workspace/tui_config.json',
        '/root/.openclaw/workspace/config/tui.json'
    ]
    
    print("🔍 检查TUI客户端配置:")
    for config_path in config_locations:
        if os.path.exists(config_path):
            print(f"✅ 找到配置文件: {config_path}")
            # 读取配置文件内容
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)  # 只读取前500字符
                print(f"   📝 内容预览: {content[:100]}...")
                return config_path
            except Exception as e:
                print(f"   ❌ 读取失败: {e}")
        else:
            print(f"ℹ️  配置文件不存在: {config_path}")
    
    return None

def analyze_edit_pattern():
    """分析编辑模式，确定TUI客户端可能的目标"""
    print("\n🔍 分析编辑模式:")
    
    # 检查最近修改的文件
    files = [
        '/root/.openclaw/workspace/framework/ai_agent.py',
        '/root/.openclaw/workspace/projects/chargecloud-opc/framework/ai_agent.py',
        '/root/.openclaw/workspace/projects/token_overseas/framework/ai_agent.py'
    ]
    
    recent_files = []
    for file_path in files:
        if os.path.exists(file_path):
            mod_time = os.stat(file_path).st_mtime
            recent_files.append((file_path, mod_time))
    
    # 按修改时间排序
    recent_files.sort(key=lambda x: x[1], reverse=True)
    
    print("📅 文件修改时间排序:")
    for i, (file_path, mod_time) in enumerate(recent_files, 1):
        time_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        print(f"   {i}. {file_path} - {time_str}")
    
    # 最可能的目标文件是最近修改的
    if recent_files:
        most_recent = recent_files[0][0]
        print(f"\n🎯 最可能的目标文件: {most_recent}")
        return most_recent
    
    return None

def main():
    print("🔧 修复多个项目中 ai_agent.py 文件导致的编辑失败问题")
    print("=" * 70)
    
    # 1. 创建所有文件的备份
    backups = create_backups()
    
    # 2. 检查TUI配置
    config_path = check_tui_config()
    
    # 3. 分析编辑模式
    target_file = analyze_edit_pattern()
    
    # 4. 提供解决方案
    print("\n💡 解决方案:")
    print("-" * 40)
    print("1. 🎯 确认TUI客户端操作的目标文件:")
    if target_file:
        print(f"   - 最可能的目标: {target_file}")
    else:
        print("   - 无法确定目标文件")
    
    print("2. 🔄 统一框架版本建议:")
    print("   - 主框架: /root/.openclaw/workspace/framework/ai_agent.py (130行)")
    print("   - ChargeCloud: /projects/chargecloud-opc/framework/ai_agent.py (581行)")  
    print("   - TokenOverseas: /projects/token_overseas/framework/ai_agent.py (581行)")
    print("   - 建议选择其中一个版本作为标准")
    
    print("3. ⚙️  TUI客户端配置检查:")
    if config_path:
        print(f"   - 配置文件: {config_path}")
        print("   - 检查其中的文件路径配置")
    else:
        print("   - 未找到明显配置文件")
    
    print("4. 🛠️  操作建议:")
    print("   - 暂停TUI客户端的自动编辑操作")
    print("   - 手动确认要编辑的具体文件")
    print("   - 更新TUI客户端的文件路径配置")
    print("   - 统一各个项目的框架版本")
    
    print(f"\n📋 备份文件列表:")
    for backup in backups:
        print(f"   - {backup}")
    
    print("\n🎯 修复完成 - 需要人工确认具体操作目标")

if __name__ == "__main__":
    main()