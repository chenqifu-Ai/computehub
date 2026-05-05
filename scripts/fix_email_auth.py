#!/usr/bin/env python3
"""
邮箱授权码集中化修复工具
将所有硬编码的授权码改为引用 mail_util.py 的 send_email()

用法: python3 scripts/fix_email_auth.py [--dry-run]
"""

import os, sys, re, glob

# 找到所有硬编码授权码的脚本
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLD_AUTH_CODES = ["xunlwhjokescbgdd", "xzxveoguxylbbgbg", "ormxhluuafwnbgei", "bzgwylbbrocdbiie"]

# 要修复的文件模式
FILE_PATTERNS = [
    "scripts/*.py",
    "ai_agent/code/*.py",
    "projects/*/*.py",
    "projects/*/scripts/*.py",
    "references/*/*.py",
]

def find_auth_files():
    files = []
    for pattern in FILE_PATTERNS:
        matched = glob.glob(os.path.join(WORKSPACE, pattern), recursive=True)
        for f in matched:
            if os.path.basename(f) in ("mail_util.py", "fix_email_auth.py", "send_email.py", "send_email_fixed.py", "send_email_163.py"):
                continue
            if "node_modules" in f:
                continue
            try:
                with open(f, "r", errors="ignore") as fh:
                    content = fh.read()
                    # 检查是否包含旧的授权码
                    for code in OLD_AUTH_CODES:
                        if code in content:
                            files.append((f, code))
                            break
            except:
                pass
    return files

def fix_file(filepath, old_code):
    """将脚本中硬编码的授权码替换为从 mail_util 读取"""
    with open(filepath, "r", errors="ignore") as f:
        content = f.read()

    lines = content.split("\n")
    new_lines = []
    changed = False
    replaced_count = 0

    # 判断是否已经用了 mail_util
    uses_mail_util = "mail_util" in content or "mail_util.py" in content

    # 替换所有出现的旧授权码
    for line in lines:
        # 跳过注释行中的授权码
        stripped = line.strip()
        if stripped.startswith("#"):
            new_lines.append(line)
            continue

        new_line = line
        for code in OLD_AUTH_CODES:
            if code in new_line:
                # 把整个赋值替换为读取 config
                if "AUTH_CODE" in new_line or "auth_code" in new_line or "password" in new_line.lower() or "pass" in new_line.lower():
                    # 替换行内的授权码值
                    new_line = new_line.replace(f'"{code}"', '""')  # 清空值
                    new_line = new_line.replace(f"'{code}'", "''")
                    replaced_count += 1

                # 替换字符串中的
                new_line = new_line.replace(code, "[AUTH_CODE_FROM_CONFIG]")
                replaced_count += 1

        if new_line != line:
            changed = True
        new_lines.append(new_line)

    # 如果替换了但没有引用 mail_util，在文件头部添加导入
    if changed and not uses_mail_util:
        # 在 imports 后面添加
        insert_point = 0
        for i, line in enumerate(new_lines):
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                insert_point = i + 1
        # 找到最后一个 import
        for i in range(len(new_lines) - 1, -1, -1):
            if new_lines[i].strip().startswith("import ") or new_lines[i].strip().startswith("from "):
                insert_point = i + 1
                break

        new_lines.insert(insert_point, "import sys")
        new_lines.insert(insert_point + 1, f"sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))")
        new_lines.insert(insert_point + 2, "from mail_util import send_email, get_config")
        new_lines.insert(insert_point + 3, "")  # blank line
        changed = True

    return "\n".join(new_lines), changed, replaced_count


def main():
    dry_run = "--dry-run" in sys.argv

    files = find_auth_files()
    
    if not files:
        print("没有找到硬编码授权码的文件 ✅")
        return

    print(f"找到 {len(files)} 个文件包含硬编码授权码:\n")
    
    for filepath, code in sorted(set(files)):
        relpath = os.path.relpath(filepath, WORKSPACE)
        print(f"  📄 {relpath}  → 包含 {code[:8]}...")

    print(f"\n{'='*60}")
    
    if dry_run:
        print(f"DRY-RUN: 以下文件将被修改，但未实际执行")
        for filepath, code in sorted(set(files)):
            relpath = os.path.relpath(filepath, WORKSPACE)
            new_content, changed, count = fix_file(filepath, code)
            if changed:
                print(f"  🔧 {relpath} ({count} 处替换)")
        print("\n运行: python3 scripts/fix_email_auth.py  # 不加 --dry-run 执行修改")
        return

    # 实际修复
    fixed = 0
    errors = 0
    for filepath, code in sorted(set(files)):
        try:
            new_content, changed, count = fix_file(filepath, code)
            if changed:
                with open(filepath, "w") as f:
                    f.write(new_content)
                print(f"  ✅ {os.path.relpath(filepath, WORKSPACE)} ({count} 处替换)")
                fixed += 1
            else:
                print(f"  ⏭️  {os.path.relpath(filepath, WORKSPACE)} (无变化)")
        except Exception as e:
            print(f"  ❌ {os.path.relpath(filepath, WORKSPACE)}: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"修复完成: {fixed} 个文件修改, {errors} 个错误")

if __name__ == "__main__":
    main()
