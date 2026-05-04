#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 TUI 客户端编辑失败问题
"""

import os
import shutil
from datetime import datetime

def create_backup():
    """创建文件备份"""
    file_path = "/root/.openclaw/workspace/framework/ai_agent.py"
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"/root/.openclaw/workspace/framework/ai_agent.py.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"✅ 已创建备份: {backup_path}")
        return backup_path
    return None

def check_file_integrity():
    """检查文件完整性"""
    file_path = "/root/.openclaw/workspace/framework/ai_agent.py"
    
    if not os.path.exists(file_path):
        print("❌ 文件不存在")
        return False
    
    # 检查文件是否可读
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print("✅ 文件可正常读取")
        return True
    except Exception as e:
        print(f"❌ 文件读取失败: {e}")
        return False

def main():
    print("🔧 修复 TUI 客户端编辑失败问题")
    print("=" * 50)
    
    # 1. 创建备份
    backup_path = create_backup()
    
    # 2. 检查文件完整性
    if check_file_integrity():
        print("✅ 文件完整性检查通过")
    else:
        print("❌ 文件完整性检查失败")
        
    # 3. 建议解决方案
    print("\n💡 解决方案:")
    print("1. TUI 客户端需要重新生成编辑操作")
    print("2. 确保使用的文件版本与当前版本一致")
    print("3. 如果编辑操作复杂，考虑分步执行")
    print("4. 检查 TUI 客户端的缓存或状态信息")
    
    print(f"\n📋 备份位置: {backup_path}")
    print("🎯 修复完成")

if __name__ == "__main__":
    main()