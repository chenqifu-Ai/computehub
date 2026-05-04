#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全编辑操作生成器 - 为TUI客户端生成可靠的edit命令
"""

import os
import json
from datetime import datetime

def analyze_target_file(target_path):
    """分析目标文件，为编辑操作做准备"""
    if not os.path.exists(target_path):
        return None
    
    with open(target_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.splitlines()
    
    return {
        'path': target_path,
        'content': content,
        'lines': lines,
        'line_count': len(lines),
        'char_count': len(content),
        'first_10_lines': lines[:10],
        'last_5_lines': lines[-5:] if len(lines) > 5 else lines
    }

def generate_safe_edit_suggestions(file_info):
    """生成安全的编辑操作建议"""
    suggestions = []
    
    # 建议1: 在文件开头添加时间戳注释
    if file_info['content'].startswith('#!/usr/bin/env python3'):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        old_text = file_info['lines'][0] + '\n' + file_info['lines'][1]
        new_text = file_info['lines'][0] + '\n' + file_info['lines'][1] + f'\n# Last edited by TUI Client: {timestamp}\n'
        
        suggestions.append({
            'name': '添加编辑时间戳',
            'description': '在文件开头添加时间戳注释',
            'oldText': old_text,
            'newText': new_text,
            'confidence': 'high'
        })
    
    # 建议2: 在类定义后添加版本信息
    class_def_line = None
    for i, line in enumerate(file_info['lines']):
        if 'class AIAgent:' in line or 'class AIAgent(' in line:
            class_def_line = i
            break
    
    if class_def_line is not None and class_def_line + 1 < len(file_info['lines']):
        old_text = file_info['lines'][class_def_line] + '\n' + file_info['lines'][class_def_line + 1]
        new_text = file_info['lines'][class_def_line] + '\n' + file_info['lines'][class_def_line + 1] + '\n    """AI Agent Framework - TUI Client Enhanced Version"""\n'
        
        suggestions.append({
            'name': '添加类文档字符串',
            'description': '在AIAgent类定义后添加文档字符串',
            'oldText': old_text,
            'newText': new_text,
            'confidence': 'medium'
        })
    
    # 建议3: 安全的配置文件更新（如果存在API配置）
    api_key_line = None
    for i, line in enumerate(file_info['lines']):
        if 'api_key' in line and '=' in line:
            api_key_line = i
            break
    
    if api_key_line is not None:
        old_text = file_info['lines'][api_key_line]
        new_text = f'{old_text.rstrip()}  # Configured by TUI Client\n'
        
        suggestions.append({
            'name': '注释API配置',
            'description': '为API密钥配置添加注释',
            'oldText': old_text,
            'newText': new_text,
            'confidence': 'high'
        })
    
    return suggestions

def main():
    print("🤖 安全编辑操作生成器")
    print("=" * 50)
    
    # 确定目标文件（基于之前的分析）
    target_file = "/root/.openclaw/workspace/framework/ai_agent.py"
    
    print(f"🎯 目标文件: {target_file}")
    
    # 分析文件
    file_info = analyze_target_file(target_file)
    if not file_info:
        print("❌ 目标文件不存在")
        return
    
    print(f"📊 文件信息: {file_info['line_count']} 行, {file_info['char_count']} 字符")
    
    # 生成编辑建议
    suggestions = generate_safe_edit_suggestions(file_info)
    
    print(f"\n💡 生成的编辑建议 ({len(suggestions)} 个):")
    print("-" * 40)
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion['name']} ({suggestion['confidence']}置信度)")
        print(f"   📝 {suggestion['description']}")
        print(f"   🔍 匹配文本: {repr(suggestion['oldText'][:50])}...")
        print()
    
    # 生成可直接使用的edit命令
    print("🚀 可直接使用的编辑操作:")
    print("-" * 40)
    
    if suggestions:
        best_suggestion = suggestions[0]  # 使用置信度最高的建议
        
        edit_command = {
            'tool': 'edit',
            'parameters': {
                'path': target_file,
                'oldText': best_suggestion['oldText'],
                'newText': best_suggestion['newText']
            },
            'description': best_suggestion['description']
        }
        
        print("Python代码格式:")
        print(f"edit(\n    path='{target_file}',\n    oldText='''{best_suggestion['oldText']}''',\n    newText='''{best_suggestion['newText']}'''\n)")
        
        print("\nJSON格式:")
        print(json.dumps(edit_command, indent=2, ensure_ascii=False))
    
    print(f"\n✅ 生成完成! 选择置信度高的操作执行编辑。")

if __name__ == "__main__":
    main()