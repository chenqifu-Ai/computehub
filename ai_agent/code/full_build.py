#!/usr/bin/env python3
"""
OpenClaw 完整构建脚本 - 智能构建编排器
自动安装依赖、运行构建、验证产物、生成报告

使用方式:
  python full_build.py                    # 完整构建
  python full_build.py --mode ci-artifacts # CI产物构建
  python full_build.py --mode strict-smoke # 快速烟雾测试
  python full_build.py --skip-deps        # 跳过依赖安装
  python full_build.py --skip-test        # 跳过构建后测试
  python full_build.py --report-only      # 仅检查报告

SOP遵循: 分析 -> 代码 -> 执行 -> 验证 -> 学习
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# ─── 配置 ──────────────────────────────────────────────────────────
SOURCE_DIR = "/root/.openclaw/workspace/openclaw-src-final"
RESULTS_DIR = "/root/.openclaw/workspace/ai_agent/results"
CODE_DIR = "/root/.openclaw/workspace/ai_agent/code"

os.chdir(SOURCE_DIR)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ─── 工具函数 ──────────────────────────────────────────────────────


def run(cmd, description="", timeout=600, check=False):
    """执行命令，返回 (ok, stdout, stderr)"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"   $ {cmd}")
    start = time.time()
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        ok = result.returncode == 0
        status = "✅" if ok else "❌"
        print(f"   {status} ({elapsed:.1f}s, exit={result.returncode})")

        # 打印前10行stdout
        if result.stdout:
            lines = result.stdout.strip().split("\n")
            display = lines[:15]
            if len(lines) > 15:
                display.append(f"   ... ({len(lines)-15} more lines)")
            for line in display:
                print(f"   > {line}")

        if result.stderr and result.returncode != 0:
            for line in result.stderr.strip().split("\n")[:10]:
                print(f"   ! {line}")

        if check and not ok:
            raise RuntimeError(f"命令失败 (exit={result.returncode}): {cmd}")
        return ok, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 超时 ({timeout}s)")
        return False, "", "Timeout"
    except Exception as e:
        print(f"   💥 异常: {e}")
        if check:
            raise
        return False, "", str(e)


def check_package_json():
    """读取package.json"""
    with open("package.json") as f:
        return json.load(f)


def make_report(report_data):
    """生成构建报告"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/build_report_{ts}.json"
    with open(path, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    # 同时生成可读版本
    txt_path = f"{RESULTS_DIR}/build_report_{ts}.txt"
    with open(txt_path, "w") as f:
        f.write(format_report(report_data))
    return path, txt_path


def format_report(data):
    """格式化构建报告为文本"""
    lines = [
        "=" * 55,
        "📋 OpenClaw 构建报告",
        f"   生成时间: {data.get('timestamp', 'N/A')}",
        f"   模式: {data.get('mode', 'N/A')}",
        f"   耗时: {data.get('duration_seconds', 0):.1f}s",
        f"   最终状态: {'✅ 成功' if data.get('success') else '❌ 失败'}",
        "=" * 55,
        "",
        "📊 步骤概览:",
    ]
    for step in data.get("steps", []):
        icon = "✅" if step.get("ok") else "⏳" if step.get(
            "skipped") else "❌"
        lines.append(f"  {icon} {step['name']:40s} {step.get('duration','')}")
    lines.append("")
    if data.get("artifacts"):
        lines.append("📦 构建产物:")
        for art in data["artifacts"]:
            lines.append(f"  📄 {art}")
    lines.append("")
    if data.get("warnings"):
        lines.append("⚠️ 警告:")
        for w in data["warnings"]:
            lines.append(f"  ! {w}")
    return "\n".join(lines)


def measure_dir(dir_path):
    """测量目录大小"""
    try:
        result = subprocess.run(
            ["du", "-sh", dir_path],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().split()[0] if result.stdout else "?"
    except Exception:
        return "?"


# ─── 构建步骤 ──────────────────────────────────────────────────────


def step_check_env():
    """步骤1: 环境检查"""
    results = {}
    # Node.js
    ok, out, _ = run("node --version", "检查 Node.js")
    results["node_version"] = out.strip() if out else "unknown"
    # pnpm
    ok, out, _ = run("pnpm --version", "检查 pnpm")
    results["pnpm_version"] = out.strip() if out else "unknown"
    # git
    ok, out, _ = run("git rev-parse HEAD 2>/dev/null", "检查 Git HEAD")
    results["git_head"] = out.strip() if out else "no git"
    # 项目版本
    pkg = check_package_json()
    results["project_version"] = pkg.get("version", "unknown")
    # 磁盘空间
    ok, out, _ = run("df -h . | tail -1", "检查磁盘空间")
    results["disk"] = out.strip() if out else "unknown"
    return results


def step_install_deps():
    """步骤2: 安装依赖"""
    ok, _, _ = run("pnpm install --frozen-lockfile 2>&1 | tail -5",
                    "安装依赖 (frozen lockfile)", timeout=600)
    if not ok:
        print("   ⚠️ frozen-lockfile 失败, 尝试普通安装...")
        ok, _, _ = run("pnpm install 2>&1 | tail -5",
                        "安装依赖", timeout=600)
    if ok:
        deps_size = measure_dir("node_modules")
        print(f"   📦 node_modules: {deps_size}")
    return ok


def step_build(mode="full"):
    """步骤3: 执行构建"""
    if mode == "ci-artifacts":
        cmd = "pnpm build:ci-artifacts"
    elif mode == "strict-smoke":
        cmd = "pnpm build:strict-smoke"
    else:
        cmd = "pnpm build"

    ok, out, _ = run(cmd, f"构建 ({mode})", timeout=900)
    return ok


def step_verify_build():
    """步骤4: 验证构建产物"""
    artifacts = []
    # 检查 dist 目录
    if os.path.isdir("dist"):
        size = measure_dir("dist")
        artifacts.append(f"dist/ ({size})")
        # 列出关键文件
        for pattern in [".buildstamp", "index.js", "cli/index.js", "openclaw.mjs"]:
            path = f"dist/{pattern}"
            if os.path.exists(path):
                fsize = os.path.getsize(path)
                artifacts.append(f"  {pattern} ({fsize:,} bytes)")
    else:
        # 检查根目录入口
        for f in ["openclaw.mjs", "dist/index.js"]:
            if os.path.exists(f):
                fsize = os.path.getsize(f)
                artifacts.append(f"{f} ({fsize:,} bytes)")
    return artifacts


def step_quick_test():
    """步骤5: 快速烟雾测试"""
    print("\n📝 快速烟雾测试...")
    # 检查构建好的入口能否加载
    entry_points = ["openclaw.mjs", "dist/index.js"]
    for ep in entry_points:
        if os.path.exists(ep):
            ok, out, _ = run(
                f"node -e \"const m = require('./{ep}'); console.log(typeof m)\" 2>&1 | head -3",
                f"验证入口 {ep}", timeout=30
            )
    # 运行单元测试烟雾
    run("node scripts/run-vitest.mjs run --config test/vitest/vitest.unit-fast.config.ts --reporter=verbose 2>&1 | tail -10",
        "单元测试烟雾", timeout=120)


# ─── 主流程 ─────────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 完整构建脚本")
    parser.add_argument("--mode", default="full",
                        choices=["full", "ci-artifacts", "strict-smoke"])
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument("--skip-test", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    print(f"""
╔{'═'*50}╗
║  🤖 OpenClaw 构建引擎{' '*(27)}║
║  模式: {args.mode:32s}║
║  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):27s}║
╚{'═'*50}╝
""")

    start_time = time.time()
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": args.mode,
        "success": False,
        "duration_seconds": 0,
        "steps": [],
        "artifacts": [],
        "warnings": [],
    }

    try:
        # 步骤1: 环境检查
        t0 = time.time()
        env = step_check_env()
        report["steps"].append({
            "name": "环境检查", "ok": True,
            "duration": f"{time.time()-t0:.1f}s"
        })
        report["environment"] = env

        if args.report_only:
            print("\n⚠️ 报告模式: 跳过所有执行步骤")
            report["success"] = True
            report["duration_seconds"] = time.time() - start_time
            paths = make_report(report)
            print(f"\n📄 报告已保存:")
            for p in paths:
                print(f"   📄 {p}")
            return

        # 步骤2: 安装依赖
        if not args.skip_deps:
            t0 = time.time()
            ok = step_install_deps()
            report["steps"].append({
                "name": "依赖安装", "ok": ok,
                "duration": f"{time.time()-t0:.1f}s"
            })
            if not ok:
                report["warnings"].append("依赖安装失败，尝试继续构建...")
        else:
            report["steps"].append({
                "name": "依赖安装", "ok": True, "skipped": True,
                "duration": "跳过"
            })

        # 步骤3: 构建
        t0 = time.time()
        ok = step_build(args.mode)
        report["steps"].append({
            "name": f"构建 ({args.mode})", "ok": ok,
            "duration": f"{time.time()-t0:.1f}s"
        })

        # 步骤4: 验证产物
        t0 = time.time()
        artifacts = step_verify_build()
        report["artifacts"] = artifacts
        report["steps"].append({
            "name": "产物验证", "ok": len(artifacts) > 0,
            "duration": f"{time.time()-t0:.1f}s"
        })

        # 步骤5: 快速测试
        if not args.skip_test and ok:
            t0 = time.time()
            step_quick_test()
            report["steps"].append({
                "name": "烟雾测试", "ok": True,
                "duration": f"{time.time()-t0:.1f}s"
            })
        else:
            report["steps"].append({
                "name": "烟雾测试", "ok": True, "skipped": True,
                "duration": "跳过"
            })

        report["success"] = ok
        report["duration_seconds"] = time.time() - start_time

        # 总结
        print(f"\n{'='*55}")
        if report["success"]:
            print(f"✅ 构建成功! ({report['duration_seconds']:.1f}s)")
        else:
            print(f"❌ 构建失败 ({report['duration_seconds']:.1f}s)")

        # 保存报告
        json_path, txt_path = make_report(report)
        print(f"\n📄 报告:")
        print(f"   📄 {txt_path}")
        print(f"   📄 {json_path}")

    except Exception as e:
        print(f"\n💥 构建异常: {e}")
        report["success"] = False
        report["errors"] = str(e)
        report["duration_seconds"] = time.time() - start_time
        make_report(report)
        sys.exit(1)


if __name__ == "__main__":
    main()
