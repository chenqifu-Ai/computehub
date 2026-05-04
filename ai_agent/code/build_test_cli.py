#!/usr/bin/env python3
"""
🛠 OpenClaw 构建与测试 CLI 统一入口

使用方式:
  python build_test_cli.py build [options]     # 构建
  python build_test_cli.py test [options]      # 测试
  python build_test_cli.py ci [options]        # CI 流水线
  python build_test_cli.py qa                  # QA 场景检查
  python build_test_cli.py env                 # 环境信息
  python build_test_cli.py list                # 列出所有组件

SOP: 分析 -> 代码 -> 执行 -> 验证 -> 学习 -> 交付
"""

import subprocess
import sys
import os
import json
from pathlib import Path

SCRIPTS = {
    "build": "full_build.py",
    "test": "full_test_suite.py",
    "ci": "ci_pipeline.py",
}

SCRIPT_DIR = Path(__file__).parent.absolute()


def print_banner():
    print("""
╔══════════════════════════════════════════╗
║  🛠  OpenClaw 构建与测试工具集          ║
║  v2026.4 - AI 智能编排器                ║
╚══════════════════════════════════════════╝
""")


def show_env():
    """显示环境信息"""
    print("\n📊 环境信息:")
    print(f"{'='*50}")

    checks = [
        ("Node.js", "node --version"),
        ("pnpm", "pnpm --version"),
        ("Git", "git --version"),
        ("Python", "python3 --version"),
        ("磁盘", "df -h . | tail -1"),
        ("内存", "free -h | grep Mem || echo 'N/A'"),
    ]

    for name, cmd in checks:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            val = r.stdout.strip()[:80] if r.stdout else r.stderr.strip()[:80]
            print(f"  {name:10s}: {val}")
        except Exception as e:
            print(f"  {name:10s}: ❌ {e}")

    # 项目版本
    pkg_path = "/root/.openclaw/workspace/openclaw-src-final/package.json"
    if os.path.exists(pkg_path):
        with open(pkg_path) as f:
            pkg = json.load(f)
        print(f"  {'项目':10s}: {pkg.get('name', '?')} v{pkg.get('version', '?')}")

    print()


def show_list():
    """列出所有可用的工具和脚本"""
    print("""
📋 可用命令:
╔{'═'*50}╗
║  build                      🤖 完整构建         ║
║  build --mode ci-artifacts  🤖 CI产物构建        ║
║  build --mode strict-smoke  🤖 快速烟雾测试构建  ║
║  build --skip-deps          🤖 跳过依赖安装      ║
║  build --skip-test          🤖 跳过构建后测试    ║
║                             ║
║  test                       🧪 单元测试 (快速)   ║
║  test --type all            🧪 全部测试          ║
║  test --type fast           🧪 快速组            ║
║  test --type unit           🧪 单元测试          ║
║  test --type e2e            🧪 端到端测试        ║
║  test --type live           🧪 实时测试          ║
║  test --type core           🧪 核心组            ║
║  test --type extension mem  🧪 指定扩展测试      ║
║  test --list                🧪 列出所有测试配置  ║
║  test --filter pattern      🧪 测试名称筛选      ║
║                             ║
║  ci                         🔄 完整CI流水线      ║
║  ci --mode check            🔄 仅检查            ║
║  ci --mode build            🔄 仅构建            ║
║  ci --mode test             🔄 仅测试            ║
║  ci --mode qa               🔄 QA场景检查        ║
║  ci --report                🔄 生成HTML报告      ║
║  ci --skip-qa               🔄 跳过QA            ║
║                             ║
║  env                        📊 环境信息          ║
║  list                       📋 本帮助            ║
╚{'═'*50}╝

💡 快速入门:
  1. 环境检查:  python ai_agent/code/build_test_cli.py env
  2. 快速测试:  python ai_agent/code/build_test_cli.py test --type fast
  3. 完整CI:    python ai_agent/code/build_test_cli.py ci
""")
    # 显示实际的Python脚本
    print("\n📁 脚本文件:")
    script_dir = Path("/root/.openclaw/workspace/ai_agent/code")
    for f in sorted(script_dir.glob("*.py")):
        size = f.stat().st_size
        print(f"  📄 {f.name:40s} ({size:,} bytes)")


def main():
    if len(sys.argv) < 2:
        print_banner()
        show_list()
        return

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if cmd == "env":
        print_banner()
        show_env()
    elif cmd == "list" or cmd == "--help" or cmd == "-h":
        print_banner()
        show_list()
    elif cmd in SCRIPTS:
        script = SCRIPTS[cmd]
        script_path = SCRIPT_DIR / script
        if not script_path.exists():
            print(f"❌ 脚本不存在: {script_path}")
            sys.exit(1)
        # 转发所有剩余参数
        os.execv(sys.executable, [sys.executable, str(script_path), *rest])
    else:
        print(f"❌ 未知命令: {cmd}")
        print(f"   可用命令: {' | '.join(SCRIPTS.keys())} | env | list")
        sys.exit(1)


if __name__ == "__main__":
    main()
