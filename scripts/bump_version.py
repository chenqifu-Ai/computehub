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
        major += 1; minor = 0; patch = 0
    elif part == "minor":
        minor += 1; patch = 0
    elif part == "patch":
        patch += 1
    else:
        print(f"❌ 未知类型: {part}")
        sys.exit(1)

    new_str = f"{major}.{minor}.{patch}"
    print(f"新版本: {new_str}")

    # 1. 更新 version.go
    content = VERSION_FILE.read_text()
    content = content.replace(f'VERSION = "{old_str}"', f'VERSION = "{new_str}"')
    VERSION_FILE.write_text(content)
    print(f"  ✅ src/version/version.go")

    # 2. 更新 version.txt
    ver_txt = ROOT / "deploy/version.txt"
    if ver_txt.exists():
        ver_txt.write_text(f"{new_str}\n")
        print(f"  ✅ deploy/version.txt")

    print(f"\n🎉 版本已更新: {old_str} → {new_str}")
    print(f"提交建议: git commit -m 'chore: bump version to v{new_str}'")
    return new_str


def show():
    old_str, _, _, _ = read_current_version()
    print(f"ComputeHub v{old_str}")
    print(f"  VERSION:    {VERSION_FILE}")
    print(f"  主入口:     {ROOT}/cmd/computehub/main.go")

    # 检查所有文件中的版本一致性
    issues = []
    for f in sorted(ROOT.rglob("*.go")):
        text = f.read_text()
        # 跳过 vendor/generated
        if "vendor/" in str(f):
            continue
        # 检查有没有其他地方硬编码不同的版本号
        for m in re.finditer(r'VERSION\s*=\s*"(\d+\.\d+\.\d+)"', text):
            if m.group(1) != old_str:
                issues.append((f, m.group(1)))

    if issues:
        print(f"⚠️  版本不一致:")
        for f, v in issues:
            print(f"     {f.relative_to(ROOT)}: {v}")
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
