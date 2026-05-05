#!/usr/bin/env python3
"""
🔄 一键迁移所有硬编码授权码 → 统一 email_utils 模块
使用方法: python3 scripts/migrate_email_scripts.py
"""

import os
import re
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__))
AI_CODE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_agent", "code")
PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects")

FIXES = []

def add_fix(path, desc, old, new):
    FIXES.append((path, desc, old, new))

def scan_and_fix():
    count = 0
    
    # 遍历 scripts/ 目录
    for fname in os.listdir(SCRIPTS_DIR):
        if not fname.endswith(".py") or fname == os.path.basename(__file__) or fname == "email_utils.py":
            continue
        fpath = os.path.join(SCRIPTS_DIR, fname)
        fix_file_smtp(fpath)
    
    # 遍历 ai_agent/code/ 目录
    if os.path.exists(AI_CODE_DIR):
        for fname in os.listdir(AI_CODE_DIR):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(AI_CODE_DIR, fname)
            fix_file_smtp(fpath)
    
    # 遍历 projects/ 目录
    if os.path.exists(PROJECTS_DIR):
        for root, dirs, files in os.walk(PROJECTS_DIR):
            for f in files:
                if f.endswith(".py"):
                    fix_file_smtp(os.path.join(root, f))
    
    return len(FIXES)

def fix_file_smtp(fpath):
    """扫描文件，如果含硬编码授权码则标记修复"""
    if not os.path.isfile(fpath):
        return
    
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return
    
    # 检查是否包含硬编码授权码
    codes_found = set()
    for code in ["xunlwhjokescbgdd", "xzxveoguxylbbgbg", "ormxhluuafwnbgei", "bzgwylbbrocdbiie"]:
        if code in content:
            codes_found.add(code)
    
    if not codes_found:
        return
    
    # 检查是否已经用了 email_utils
    if "from email_utils import" in content or "import email_utils" in content:
        print(f"  ⏭️  {os.path.basename(fpath)} - 已迁移, 跳过")
        return
    
    # 构建替换方案
    basename = os.path.basename(fpath)
    
    # 检查文件是否包含 send_email 类的函数定义
    has_smtp_import = "import smtplib" in content or "from smtplib" in content
    has_auth_line = "login(" in content and "19525456" in content
    has_mail_config = "smtp.qq.com" in content or "19525456@qq.com" in content
    
    if has_smtp_import and has_auth_line:
        # 找到并替换 login 行
        new_content = content
        
        # 1. 添加 import 行
        # 在文件开头的 import 区域添加
        import_pattern = re.compile(r'^(import\s+\w+|from\s+\w+\s+import)', re.MULTILINE)
        matches = list(import_pattern.finditer(content))
        
        if "email_utils" not in content:
            # 在第一个 import 之前添加
            first_import = matches[0] if matches else None
            if first_import:
                pos = first_import.start()
                insert = "from scripts.email_utils import send_email_safe\n"
                if content[pos:pos+len(insert)] != insert:
                    new_content = content[:pos] + insert + content[pos:]
            else:
                new_content = "from scripts.email_utils import send_email_safe\n" + content
        
        # 2. 替换 sendmail 逻辑（复杂的需要手动处理，这里加注释提醒）
        # 在文件末尾添加 TODO
        todo_note = "\n\n# TODO: 迁移到统一邮件模块\n# 建议替换为:\n#   from email_utils import send_email_safe\n#   send_email_safe(SUBJECT, BODY)\n"
        
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            if "# TODO: 迁移" not in new_content:
                f.write(todo_note)
        
        add_fix(fpath, "🚩 标记待迁移 (硬编码授权码)", 
                f"{codes_found}", "迁移到 email_utils")
        print(f"  🚩  {basename} - 标记迁移点 + 注释")
    else:
        # 简单替换授权码（如果只是配置字典里的值）
        new_content = content
        changed = False
        for code in codes_found:
            # 替换配置字典中的值
            for pattern in [
                f"'{code}'",
                f'"{code}"',
            ]:
                if pattern in new_content:
                    new_content = new_content.replace(pattern, '"__USE_CONFIG__"')
                    changed = True
        
        if changed:
            # 添加 import
            if "email_utils" not in new_content:
                insert = "\nfrom scripts.email_utils import load_config\n"
                # 在文件开头添加
                first_line = new_content.find("\n") + 1
                new_content = new_content[:first_line] + insert + new_content[first_line:]
            
            # 添加配置加载
            cfg_load = '\n# 从统一配置加载\n_cfg = load_config()\nAUTH_CODE = _cfg["auth_code"]\n'
            new_content += cfg_load
            
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            add_fix(fpath, "🔄 自动替换授权码引用", 
                    f"{codes_found}", "config/email.json")
            print(f"  🔄  {basename} - 授权码引用已替换")
    
    return

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 邮箱授权码迁移工具")
    print("=" * 60)
    
    total = scan_and_fix()
    
    print()
    print(f"📊 处理结果:")
    print(f"   共标记/修改 {len(FIXES)} 个文件")
    print(f"   手动迁移: {sum(1 for f in FIXES if f[1].startswith('🚩'))} 个")
    print(f"   自动替换: {sum(1 for f in FIXES if f[1].startswith('🔄'))} 个")
    
    if len(FIXES) > 0:
        print(f"\n📋 变更清单:")
        for path, desc, old, new in FIXES:
            name = os.path.basename(path)
            print(f"  {desc:30s} {name:30s} {old} → {new}")
    
    print(f"\n✅ 完成!")
    print(f"📌 以后新增脚本请用:")
    print(f"   from scripts.email_utils import send_email_safe")
    print(f"   send_email_safe('主题', '正文')")
