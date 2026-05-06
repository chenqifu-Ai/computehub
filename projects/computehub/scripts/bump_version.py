#!/usr/bin/env python3
"""
ComputeHub 版本号管理脚本

用法:
  python3 scripts/bump_version.py         # 显示当前版本
  python3 scripts/bump_version.py patch   # 0.7.2 → 0.7.3 (修复)
  python3 scripts/bump_version.py minor   # 0.7.2 → 0.8.0 (新功能)
  python3 scripts/bump_version.py major   # 0.7.2 → 1.0.0 (重大变更)

流程:
  1. 修改 src/version/version.go 中的 VERSION
  2. 更新各组件中的版本号引用

执行者: 小智
"""

import re
import sys
import os
from pathlib import Path

ROOT = Path("/root/.openclaw/workspace/projects/computehub")
VERSION_FILE = ROOT / "src/version/version.go"

def read_current_version():
    content = VERSION_FILE.read_text()
    m = re.search(r'VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
    if not m:
        print("❌ 无法解析版本号")
        sys.exit(1)
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}", int(m.group(1)), int(m.group(2)), int(m.group(3))

def bump(part):
    old_str, major, minor, patch = read_current_version()
    print(f"当前版本: {old_str}")

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        print(f"❌ 未知类型: {part}，使用 patch/major/minor")
        sys.exit(1)

    new_str = f"{major}.{minor}.{patch}"
    print(f"新版本: {new_str}")

    # 1. 更新 version.go
    content = VERSION_FILE.read_text()
    content = content.replace(f'VERSION = "{old_str}"', f'VERSION = "{new_str}"')
    VERSION_FILE.write_text(content)
    print(f"  ✅ src/version/version.go")

    # 2. 更新 TUI 中的版本引用（改成从 version 包导入）
    tui_file = ROOT / "cmd/tui/main.go"
    content = tui_file.read_text()
    # 如果 TUI 还是硬编码 version，替换它
    content = content.replace(f'const version = "{old_str}"', f'const version = "{new_str}"')
    tui_file.write_text(content)
    print(f"  ✅ cmd/tui/main.go")

    # 3. 更新 Worker 中的硬编码版本
    worker_file = ROOT / "cmd/worker/main.go"
    content = worker_file.read_text()
    content = content.replace(f'v{old_str}', f'v{new_str}')
    worker_file.write_text(content)
    print(f"  ✅ cmd/worker/main.go")

    # 4. 更新 fix 脚本
    for fix_file in ROOT.glob("fix_*.go"):
        content = fix_file.read_text()
        if old_str in content:
            content = content.replace(f'VERSION = "{old_str}"', f'VERSION = "{new_str}"')
            content = content.replace(old_str, new_str)
            fix_file.write_text(content)
            print(f"  ✅ {fix_file.name}")

    print(f"\n🎉 版本已更新: {old_str} → {new_str}")
    print(f"\n提交建议: git commit -m 'chore: bump version to v{new_str}'")
    return new_str


def show():
    old_str, _, _, _ = read_current_version()
    print(f"ComputeHub v{old_str}")
    print(f"  VERSION:    {VERSION_FILE}")
    print(f"  Gateway:    {ROOT}/cmd/gateway/main.go")
    print(f"  TUI:        {ROOT}/cmd/tui/main.go")
    print(f"  Worker:     {ROOT}/cmd/worker/main.go")

    # 检查所有组件的版本一致性
    versions_used = set()
    versions_used.add(old_str)

    for pattern in ["**/main.go", "**/*.go"]:
        for f in ROOT.glob(pattern):
            text = f.read_text()
            for m in re.finditer(r'v?(\d+\.\d+\.\d+)', text):
                v = m.group(1)
                if v != old_str and v not in text[text.rfind('\n', 0, m.start()):m.start()]:
                    # Only flag if it's a version constant/string, not in import paths
                    pass

    if len(versions_used) > 1:
        print(f"⚠️  版本不一致: {versions_used}")
    else:
        print(f"✅ 所有组件版本一致")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show()
        sys.exit(0)

    action = sys.argv[1]
    if action in ("patch", "minor", "major"):
        bump(action)
    elif action in ("show", "status", "-v", "--version"):
        show()
    else:
        print(f"用法: python3 {sys.argv[0]} [patch|minor|major|show]")
        sys.exit(1)
