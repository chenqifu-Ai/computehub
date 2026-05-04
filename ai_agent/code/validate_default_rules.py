#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证系统是否遵循默认规则
"""

import os
import json
from datetime import datetime

def validate_sop_compliance():
    """验证SOP流程合规性"""
    print("🔍 验证SOP流程合规性...")
    
    # 检查AI智能体目录结构
    code_dir = "/root/.openclaw/workspace/ai_agent/code/"
    results_dir = "/root/.openclaw/workspace/ai_agent/results/"
    
    if os.path.exists(code_dir):
        code_files = [f for f in os.listdir(code_dir) if f.endswith('.py')]
        print(f"   ✅ 代码目录存在，包含 {len(code_files)} 个Python脚本")
    else:
        print("   ⚠️  代码目录不存在")
        return False
    
    if os.path.exists(results_dir):
        result_files = os.listdir(results_dir)
        print(f"   ✅ 结果目录存在，包含 {len(result_files)} 个结果文件")
    else:
        print("   ⚠️  结果目录不存在")
        return False
    
    return True

def validate_config_backup():
    """验证配置备份系统"""
    print("🔍 验证配置备份系统...")
    
    snapshot_dir = "/root/.openclaw/workspace/config/version_control/snapshots/"
    changelog_file = "/root/.openclaw/workspace/config/version_control/changelog.json"
    
    if os.path.exists(snapshot_dir):
        snapshots = [d for d in os.listdir(snapshot_dir) if d.startswith('snapshot_')]
        if snapshots:
            print(f"   ✅ 快照系统正常，包含 {len(snapshots)} 个快照")
            latest_snapshot = max(snapshots)
            print(f"   📅 最新快照: {latest_snapshot}")
        else:
            print("   ⚠️  快照目录为空")
            return False
    else:
        print("   ❌ 快照目录不存在")
        return False
    
    if os.path.exists(changelog_file):
        print("   ✅ 变更日志存在")
    else:
        print("   ❌ 变更日志不存在")
        return False
    
    return True

def validate_security_boundaries():
    """验证安全边界"""
    print("🔍 验证安全边界...")
    
    # 检查MEMORY.md中的安全规则
    memory_file = "/root/.openclaw/workspace/MEMORY.md"
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "严禁扫描其他电脑" in content and "192.168.2.7" in content:
                print("   ✅ 网络安全边界已设置")
            else:
                print("   ⚠️  网络安全边界未正确设置")
                return False
    else:
        print("   ❌ MEMORY.md不存在")
        return False
    
    return True

def validate_default_rules_file():
    """验证默认规则文件"""
    print("🔍 验证默认规则文件...")
    
    default_rules_file = "/root/.openclaw/workspace/DEFAULT_RULES.md"
    if os.path.exists(default_rules_file):
        print("   ✅ 默认规则文件存在")
        # 检查文件是否包含关键内容
        with open(default_rules_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "核心执行原则" in content and "安全边界" in content:
                print("   ✅ 默认规则文件内容完整")
                return True
            else:
                print("   ⚠️  默认规则文件内容不完整")
                return False
    else:
        print("   ❌ 默认规则文件不存在")
        return False

def main():
    print("📋 验证默认规则合规性检查")
    print("=" * 50)
    
    checks = [
        validate_sop_compliance,
        validate_config_backup,
        validate_security_boundaries,
        validate_default_rules_file
    ]
    
    results = []
    for check in checks:
        result = check()
        results.append(result)
        print()
    
    success_count = sum(results)
    total_count = len(results)
    
    print("=" * 50)
    print(f"📊 验证结果: {success_count}/{total_count} 项通过")
    
    if success_count == total_count:
        print("✅ 所有默认规则验证通过！系统完全合规。")
        return True
    else:
        print("⚠️  部分规则验证失败，请检查并修复。")
        return False

if __name__ == "__main__":
    main()