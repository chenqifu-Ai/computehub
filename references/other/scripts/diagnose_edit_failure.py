#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断 TUI 客户端编辑失败问题
"""

import os
import subprocess
from datetime import datetime

def main():
    print("🔍 诊断 TUI 客户端编辑失败问题")
    print("=" * 50)
    
    # 检查文件状态
    file_path = "/root/.openclaw/workspace/framework/ai_agent.py"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    # 获取文件信息
    stat = os.stat(file_path)
    mod_time = datetime.fromtimestamp(stat.st_mtime)
    print(f"📄 文件: {file_path}")
    print(f"📏 大小: {stat.st_size} 字节")
    print(f"⏰ 最后修改: {mod_time}")
    
    # 检查文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📝 行数: {len(content.splitlines())}")
    print(f"🔤 字符数: {len(content)}")
    
    # 检查常见的编辑问题
    print("\n🔎 检查常见问题:")
    
    # 1. 检查文件编码
    try:
        content.encode('utf-8')
        print("✅ 文件编码: UTF-8 (正常)")
    except UnicodeEncodeError:
        print("❌ 文件编码: 非 UTF-8 (可能有问题)")
    
    # 2. 检查换行符
    if '\r\n' in content:
        print("⚠️  换行符: Windows 风格 (CRLF)")
    elif '\r' in content:
        print("⚠️  换行符: Mac 风格 (CR)")
    else:
        print("✅ 换行符: Unix 风格 (LF)")
    
    # 3. 检查文件权限
    if os.access(file_path, os.W_OK):
        print("✅ 文件权限: 可写")
    else:
        print("❌ 文件权限: 不可写")
    
    # 4. 检查文件是否被其他进程占用
    try:
        result = subprocess.run(['lsof', file_path], capture_output=True, text=True)
        if result.stdout:
            print("⚠️  文件被其他进程占用:")
            print(result.stdout)
        else:
            print("✅ 文件未被其他进程占用")
    except FileNotFoundError:
        print("ℹ️  lsof 命令不可用，跳过进程检查")
    
    print("\n💡 建议:")
    print("1. 检查 TUI 客户端是否使用了正确的文件版本")
    print("2. 确认编辑操作的目标文本与文件内容完全匹配")
    print("3. 检查文件编码和换行符一致性")
    print("4. 如果问题持续，考虑重新生成编辑操作")

if __name__ == "__main__":
    main()