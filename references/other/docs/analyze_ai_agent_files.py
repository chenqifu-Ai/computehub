#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析多个项目中的 ai_agent.py 文件差异
"""

import os
import difflib
from datetime import datetime

def compare_files(file1, file2):
    """比较两个文件的差异"""
    with open(file1, 'r', encoding='utf-8') as f1:
        content1 = f1.readlines()
    with open(file2, 'r', encoding='utf-8') as f2:
        content2 = f2.readlines()
    
    diff = difflib.unified_diff(content1, content2, fromfile=file1, tofile=file2)
    return list(diff)

def analyze_file(file_path):
    """分析单个文件"""
    if not os.path.exists(file_path):
        return None
    
    stat = os.stat(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return {
        'path': file_path,
        'size': stat.st_size,
        'lines': len(content.splitlines()),
        'chars': len(content),
        'modified': datetime.fromtimestamp(stat.st_mtime),
        'exists': True
    }

def main():
    print("🔍 分析多个项目中的 ai_agent.py 文件")
    print("=" * 60)
    
    # 分析所有相关的 ai_agent.py 文件
    files_to_analyze = [
        '/root/.openclaw/workspace/framework/ai_agent.py',
        '/root/.openclaw/workspace/projects/chargecloud-opc/framework/ai_agent.py',
        '/root/.openclaw/workspace/projects/token_overseas/framework/ai_agent.py'
    ]
    
    file_info = []
    for file_path in files_to_analyze:
        info = analyze_file(file_path)
        if info:
            file_info.append(info)
    
    # 显示文件信息
    print("📊 文件统计信息:")
    print("-" * 40)
    for info in file_info:
        print(f"📄 {os.path.basename(info['path'])}:")
        print(f"   📍 路径: {info['path']}")
        print(f"   📏 大小: {info['size']} 字节")
        print(f"   📝 行数: {info['lines']}")
        print(f"   🔤 字符: {info['chars']}")
        print(f"   ⏰ 修改: {info['modified']}")
        print()
    
    # 比较主要文件与其他文件的差异
    if len(file_info) > 1:
        print("🔄 文件差异分析:")
        print("-" * 40)
        
        main_file = file_info[0]['path']
        for i, info in enumerate(file_info[1:], 1):
            diff = compare_files(main_file, info['path'])
            print(f"📋 {os.path.basename(main_file)} vs {os.path.basename(info['path'])}:")
            if diff:
                print(f"   ⚠️  存在 {len(diff)} 处差异")
                # 显示前5个差异
                for line in diff[:10]:
                    print(f"      {line.rstrip()}")
                if len(diff) > 10:
                    print(f"      ... (还有 {len(diff) - 10} 处差异)")
            else:
                print("   ✅ 文件内容相同")
            print()
    
    # 建议
    print("💡 问题诊断与建议:")
    print("-" * 40)
    print("1. TUI客户端可能在尝试编辑错误的文件路径")
    print("2. 不同项目中的 ai_agent.py 文件版本不一致")
    print("3. 需要确认TUI客户端具体操作哪个文件")
    print("4. 建议统一各个项目的框架版本")
    print("5. 检查TUI客户端的文件路径配置")

if __name__ == "__main__":
    main()