#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置版本控制 - 回退到指定快照
"""

import os
import json
import shutil
from datetime import datetime

CONFIG_DIR = "/root/.openclaw/workspace/config"
SNAPSHOT_DIR = "/root/.openclaw/workspace/config/version_control/snapshots"
CHANGELOG_FILE = "/root/.openclaw/workspace/config/version_control/changelog.json"

def list_snapshots():
    """列出所有可用的快照"""
    if not os.path.exists(SNAPSHOT_DIR):
        print("❌ 没有找到快照目录")
        return []
    
    snapshots = []
    for item in os.listdir(SNAPSHOT_DIR):
        snapshot_path = os.path.join(SNAPSHOT_DIR, item)
        if os.path.isdir(snapshot_path) and item.startswith('snapshot_'):
            snapshots.append(item)
    
    snapshots.sort(reverse=True)  # 最新的在前面
    return snapshots

def get_snapshot_info(snapshot_id):
    """获取快照详细信息"""
    changelog = []
    if os.path.exists(CHANGELOG_FILE):
        try:
            with open(CHANGELOG_FILE, 'r', encoding='utf-8') as f:
                changelog = json.load(f)
        except Exception as e:
            print(f"⚠️  读取变更日志失败: {e}")
    
    for record in changelog:
        if record["snapshot_id"] == snapshot_id:
            return record
    return None

def rollback_to_snapshot(snapshot_id, dry_run=False):
    """回退到指定快照"""
    print(f"🔄 准备回退到快照: {snapshot_id}")
    
    # 验证快照是否存在
    snapshot_path = os.path.join(SNAPSHOT_DIR, snapshot_id)
    if not os.path.exists(snapshot_path):
        print(f"❌ 快照不存在: {snapshot_path}")
        return False
    
    # 获取快照信息
    snapshot_info = get_snapshot_info(snapshot_id)
    if not snapshot_info:
        print(f"⚠️  无法获取快照 {snapshot_id} 的详细信息")
    
    # 列出要恢复的文件
    files_to_restore = []
    for filename in os.listdir(snapshot_path):
        if os.path.isfile(os.path.join(snapshot_path, filename)):
            files_to_restore.append(filename)
    
    if not files_to_restore:
        print("❌ 快照中没有找到任何文件")
        return False
    
    print(f"📋 将要恢复 {len(files_to_restore)} 个文件:")
    for filename in files_to_restore:
        print(f"   - {filename}")
    
    if dry_run:
        print("\n🔍 这是预览模式，不会实际执行恢复操作")
        return True
    
    # 创建当前配置的备份（以防回退出问题）
    backup_name = f"pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join(SNAPSHOT_DIR, backup_name)
    os.makedirs(backup_path, exist_ok=True)
    
    print(f"\n💾 创建回退前备份: {backup_name}")
    for filename in files_to_restore:
        src_path = os.path.join(CONFIG_DIR, filename)
        if os.path.exists(src_path):
            dst_path = os.path.join(backup_path, filename)
            shutil.copy2(src_path, dst_path)
            print(f"   ✅ 备份: {filename}")
    
    # 执行回退
    print(f"\n🔄 开始恢复文件...")
    success_count = 0
    for filename in files_to_restore:
        src_path = os.path.join(snapshot_path, filename)
        dst_path = os.path.join(CONFIG_DIR, filename)
        try:
            shutil.copy2(src_path, dst_path)
            print(f"   ✅ 恢复: {filename}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 恢复失败: {filename} - {e}")
    
    print(f"\n✅ 回退完成!")
    print(f"   成功恢复: {success_count}/{len(files_to_restore)} 个文件")
    print(f"   快照ID: {snapshot_id}")
    if snapshot_info:
        print(f"   快照时间: {snapshot_info.get('timestamp', 'Unknown')}")
        print(f"   快照描述: {snapshot_info.get('description', 'No description')}")
    
    return success_count == len(files_to_restore)

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python rollback_to_snapshot.py <snapshot_id> [--dry-run]")
        print("\n可用的快照:")
        snapshots = list_snapshots()
        if snapshots:
            for snapshot in snapshots[:10]:  # 只显示最近10个
                info = get_snapshot_info(snapshot)
                timestamp = info.get('timestamp', 'Unknown') if info else 'Unknown'
                desc = info.get('description', 'No description') if info else 'No description'
                print(f"  {snapshot}")
                print(f"    时间: {timestamp}")
                print(f"    描述: {desc}")
                print()
        else:
            print("  没有可用的快照")
        return
    
    snapshot_id = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    
    rollback_to_snapshot(snapshot_id, dry_run)

if __name__ == "__main__":
    main()