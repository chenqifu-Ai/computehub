#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置版本控制 - 创建快照
"""

import os
import json
import shutil
import hashlib
from datetime import datetime
import glob

# 配置文件目录
CONFIG_DIR = "/root/.openclaw/workspace/config"
SNAPSHOT_DIR = "/root/.openclaw/workspace/config/version_control/snapshots"
CHANGELOG_FILE = "/root/.openclaw/workspace/config/version_control/changelog.json"

# 要跟踪的配置文件模式
CONFIG_PATTERNS = [
    "email.conf",
    "163_email.conf", 
    "model.conf",
    "company_account.json",
    "bailian_config*.json",
    "*.conf",
    "*.json"
]

def calculate_file_hash(filepath):
    """计算文件的MD5哈希值"""
    if not os.path.exists(filepath):
        return None
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_current_config_state():
    """获取当前配置状态"""
    state = {
        "timestamp": datetime.now().isoformat(),
        "files": {}
    }
    
    # 收集所有匹配的配置文件
    all_files = []
    for pattern in CONFIG_PATTERNS:
        pattern_path = os.path.join(CONFIG_DIR, pattern)
        matched_files = glob.glob(pattern_path)
        all_files.extend(matched_files)
    
    # 去重并处理
    all_files = list(set(all_files))
    
    for filepath in all_files:
        filename = os.path.basename(filepath)
        if filename.startswith('.') or filename == 'changelog.json':
            continue
            
        file_info = {
            "path": filepath,
            "hash": calculate_file_hash(filepath),
            "size": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
            "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat() if os.path.exists(filepath) else None
        }
        state["files"][filename] = file_info
    
    return state

def create_snapshot(description="Automatic snapshot"):
    """创建配置快照"""
    print("📸 创建配置快照...")
    
    # 获取当前状态
    current_state = get_current_config_state()
    timestamp = current_state["timestamp"].replace(":", "-").replace(".", "-")
    snapshot_name = f"snapshot_{timestamp}"
    snapshot_path = os.path.join(SNAPSHOT_DIR, snapshot_name)
    
    # 创建快照目录
    os.makedirs(snapshot_path, exist_ok=True)
    
    # 复制所有配置文件到快照目录
    for filename, file_info in current_state["files"].items():
        if file_info["hash"] is not None:
            src_path = file_info["path"]
            dst_path = os.path.join(snapshot_path, filename)
            try:
                shutil.copy2(src_path, dst_path)
                print(f"  ✅ 备份: {filename}")
            except Exception as e:
                print(f"  ❌ 备份失败: {filename} - {e}")
    
    # 更新变更日志
    changelog = []
    if os.path.exists(CHANGELOG_FILE):
        try:
            with open(CHANGELOG_FILE, 'r', encoding='utf-8') as f:
                changelog = json.load(f)
        except:
            pass
    
    snapshot_record = {
        "snapshot_id": snapshot_name,
        "timestamp": current_state["timestamp"],
        "description": description,
        "files_count": len(current_state["files"]),
        "files": {k: v["hash"] for k, v in current_state["files"].items()}
    }
    changelog.append(snapshot_record)
    
    # 保存变更日志
    with open(CHANGELOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(changelog, f, indent=2, ensure_ascii=False)
    
    # 保存当前状态摘要
    current_state_file = "/root/.openclaw/workspace/config/version_control/current_state.json"
    with open(current_state_file, 'w', encoding='utf-8') as f:
        json.dump(current_state, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 快照创建成功!")
    print(f"   快照ID: {snapshot_name}")
    print(f"   文件数: {len(current_state['files'])}")
    print(f"   时间戳: {current_state['timestamp']}")
    print(f"   描述: {description}")
    
    return snapshot_name

def main():
    import sys
    description = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Manual snapshot"
    create_snapshot(description)

if __name__ == "__main__":
    main()