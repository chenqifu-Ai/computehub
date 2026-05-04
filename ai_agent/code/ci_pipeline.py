#!/usr/bin/env python3
"""
OpenClaw CI 流水线 - 全自动持续集成编排器
整合构建、测试、QA场景、产物验证一条龙

使用方式:
  python ci_pipeline.py                    # 完整CI流水线
  python ci_pipeline.py --mode check       # 仅检查 (lint + 格式)
  python ci_pipeline.py --mode build       # 仅构建
  python ci_pipeline.py --mode test        # 仅测试
  python ci_pipeline.py --mode qa          # 仅QA场景
  python ci_pipeline.py --mode full        # 全流程 (default)
  python ci_pipeline.py --skip-qa          # 跳过QA场景
  python ci_pipeline.py --report           # 生成HTML报告

SOP遵循: 分析 -> 代码 -> 执行 -> 验证 -> 学习 -> 连续交付
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

SOURCE_DIR = "/root/.openclaw/workspace/openclaw-src-final"
RESULTS_DIR = "/root/.openclaw/workspace/ai_agent/results"
os.chdir(SOURCE_DIR)
os.makedirs(f"{RESULTS_DIR}/ci", exist_ok=True)

STAGES = []


def stage(name):
    """装饰器：注册流水线阶段"""
    def decorator(func):
        STAGES.append((name, func))
        return func
    return decorator


def run(cmd, description="", timeout=300, capture=True):
    """执行命令"""
    print(f"\n{'─'*50}")
    print(f"▶ {description}")
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture, text=True, timeout=timeout
        )
        ok = result.returncode == 0
        elapsed = time.time() - t0
        icon = "✅" if ok else "❌"
        print(f"  {icon} ({elapsed:.1f}s, exit={result.returncode})")

        if capture and result.stdout:
            lines = result.stdout.strip().split("\n")
            for line in lines[-5:]:
                if line.strip():
                    print(f"    {line.strip()[:120]}")
        if not ok and capture and result.stderr:
            for line in result.stderr.strip().split("\n")[-5:]:
                if line.strip():
                    print(f"    ! {line.strip()[:120]}")

        return ok, result
    except subprocess.TimeoutExpired:
        print(f"  ⏰ 超时 ({timeout}s)")
        return False, None


# ─── 流水线阶段 ────────────────────────────────────────────────────


@stage("环境检查")
def env_check():
    checks = {}
    ok1, r = run("node --version", "Node.js 版本")
    checks["node"] = r.stdout.strip() if r else "?"
    ok2, r = run("pnpm --version", "pnpm 版本")
    checks["pnpm"] = r.stdout.strip() if r else "?"
    ok3, r = run("git rev-parse HEAD", "Git HEAD")
    checks["git"] = r.stdout.strip()[:12] if r else "?"
    ok4, r = run("df -h . | tail -1", "磁盘空间")
    checks["disk"] = r.stdout.strip() if r else "?"

    with open("package.json") as f:
        pkg = json.load(f)
    checks["version"] = pkg.get("version", "?")

    print(f"\n  环境摘要:")
    for k, v in checks.items():
        print(f"    {k:10s}: {v}")
    return all([ok1, ok2, ok3])


@stage("代码检查")
def code_check():
    lints = []
    ok1, _ = run("pnpm check:no-conflict-markers", "冲突标记检查")
    lints.append(("冲突标记", ok1))
    ok2, _ = run("pnpm tool-display:check", "工具显示检查")
    lints.append(("工具显示", ok2))
    ok3, _ = run("pnpm lint --format unix 2>&1 | tail -5", "代码风格检查", timeout=120)
    lints.append(("代码风格", ok3))
    return all(ok for _, ok in lints), lints


@stage("依赖安装")
def deps_install():
    ok1, _ = run("pnpm install --frozen-lockfile 2>&1 | tail -3",
                  "安装依赖 (frozen)", timeout=600)
    if not ok1:
        print("  ⚠️ frozen-lockfile 失败, 尝试普通安装...")
        ok1, _ = run("pnpm install 2>&1 | tail -3", "安装依赖", timeout=600)
    # 检查大小
    run("du -sh node_modules 2>/dev/null", "node_modules 大小")
    return ok1


@stage("构建")
def build_project():
    return run("pnpm build 2>&1 | tail -10", "完整构建", timeout=900)


@stage("构建验证")
def verify_build():
    artifacts = []
    checks = []

    # dist 目录
    if os.path.isdir("dist"):
        size = subprocess.run(
            "du -sh dist", shell=True, capture_output=True, text=True
        ).stdout.split()[0]
        artifacts.append(f"dist/ ({size})")

    # 关键文件
    for f in ["openclaw.mjs", "dist/index.js", "dist/.buildstamp"]:
        if os.path.exists(f):
            size = os.path.getsize(f)
            artifacts.append(f"  {f} ({size:,} bytes)")
            checks.append(True)
        else:
            checks.append(False)

    for art in artifacts:
        print(f"  📄 {art}")

    return all(checks), artifacts


@stage("单元测试（快速）")
def unit_test_fast():
    return run(
        "node scripts/run-vitest.mjs run --config test/vitest/vitest.unit-fast.config.ts 2>&1 | tail -10",
        "unit-fast 测试", timeout=300
    )


@stage("基础设施测试")
def infra_test():
    return run(
        "node scripts/run-vitest.mjs run --config test/vitest/vitest.infra.config.ts 2>&1 | tail -10",
        "infra 测试", timeout=300
    )


@stage("边界测试")
def boundary_test():
    return run(
        "node scripts/run-vitest.mjs run --config test/vitest/vitest.boundary.config.ts 2>&1 | tail -10",
        "boundary 测试", timeout=300
    )


@stage("插件测试")
def plugin_test():
    return run(
        "node scripts/run-vitest.mjs run --config test/vitest/vitest.plugins.config.ts 2>&1 | tail -10",
        "plugins 测试", timeout=300
    )


@stage("QA场景检查")
def qa_check():
    """检查QA场景目录完整性"""
    results = []
    scenarios_dir = "qa/scenarios"
    themes = os.listdir(scenarios_dir) if os.path.isdir(scenarios_dir) else []

    print(f"  📂 QA场景主题 ({len(themes)}):")
    for theme in sorted(themes):
        theme_dir = os.path.join(scenarios_dir, theme)
        if os.path.isdir(theme_dir):
            files = [f for f in os.listdir(theme_dir) if f.endswith(".md")]
            print(f"    {theme:15s}: {len(files)} 场景")
            results.append(("theme", theme, len(files)))

    # 检查新场景提案
    if os.path.exists("qa/new-scenarios-2026-04.md"):
        with open("qa/new-scenarios-2026-04.md") as f:
            content = f.read()
        scenario_count = content.count("## ")
        print(f"  📋 新场景提案: {scenario_count} 个")
        results.append(("proposals", scenario_count))

    # 检查前沿测试计划
    if os.path.exists("qa/frontier-harness-plan.md"):
        print(f"  🎯 前沿测试计划: 存在")
        results.append(("frontier-plan", True))

    return True, results


@stage("审计检查")
def audit():
    """运行代码审计脚本"""
    checks = []
    ok1, _ = run(
        "node scripts/audit-seams.mjs 2>&1 | tail -5",
        "接缝审计", timeout=60
    )
    checks.append(("接缝", ok1))

    ok2, _ = run(
        "node scripts/check-architecture-smells.mjs 2>&1 | tail -5",
        "架构味道检查", timeout=60
    )
    checks.append(("架构", ok2))

    return all(ok for _, ok in checks), checks


# ─── 报告生成 ──────────────────────────────────────────────────────


def generate_html_report(phase_results, duration, version):
    """生成HTML格式报告"""
    now = datetime.now()
    passed = sum(1 for _, ok, _ in phase_results if ok)
    failed = sum(1 for _, ok, _ in phase_results if not ok)
    total = len(phase_results)

    rows = ""
    for name, ok, detail in phase_results:
        icon = "✅" if ok else "❌"
        detail_str = str(detail)[:60] if detail else ""
        rows += f"""
        <tr>
          <td>{icon}</td>
          <td>{name}</td>
          <td class="{'pass' if ok else 'fail'}">{ 'PASS' if ok else 'FAIL' }</td>
          <td>{detail_str}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>CI Report - OpenClaw {version}</title>
  <style>
    body {{ font-family: -apple-system, 'Segoe UI', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
    h1 {{ color: #58a6ff; }}
    h2 {{ color: #8b949e; }}
    .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; min-width: 150px; }}
    .card .num {{ font-size: 2em; font-weight: bold; }}
    .pass {{ color: #3fb950; }}
    .fail {{ color: #f85149; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #30363d; }}
    th {{ background: #161b22; }}
    tr:hover {{ background: #1c2128; }}
    .footer {{ margin-top: 30px; color: #8b949e; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>🤖 OpenClaw CI Pipeline</h1>
  <h2>{version} — {now.strftime('%Y-%m-%d %H:%M:%S')}</h2>

  <div class="summary">
    <div class="card">
      <div class="num">{total}</div>
      <div>Stages</div>
    </div>
    <div class="card">
      <div class="num pass">{passed}</div>
      <div>Passed</div>
    </div>
    <div class="card">
      <div class="num fail">{failed}</div>
      <div>Failed</div>
    </div>
    <div class="card">
      <div class="num">{duration:.1f}s</div>
      <div>Duration</div>
    </div>
  </div>

  <table>
    <tr><th>#</th><th>Stage</th><th>Status</th><th>Detail</th></tr>
    {rows}
  </table>

  <div class="footer">
    Generated by OpenClaw CI Pipeline • {now.isoformat()}
  </div>
</body>
</html>"""

    path = f"{RESULTS_DIR}/ci/report_{now.strftime('%Y%m%d_%H%M%S')}.html"
    with open(path, "w") as f:
        f.write(html)
    return path


# ─── 流水线编排器 ──────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw CI 流水线")
    parser.add_argument("--mode", default="full",
                        choices=["check", "build", "test", "qa", "full"])
    parser.add_argument("--skip-qa", action="store_true")
    parser.add_argument("--report", action="store_true",
                        help="生成HTML报告")
    args = parser.parse_args()

    print(f"""
╔{'═'*48}╗
║  🔄 OpenClaw CI Pipeline{' '*(25)}║
║  模式: {args.mode:34s}║
║  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):27s}║
╚{'═'*48}╝
""")

    # 选择阶段
    mode_map = {
        "check": ["环境检查", "代码检查"],
        "build": ["环境检查", "代码检查", "依赖安装", "构建", "构建验证"],
        "test": ["环境检查", "依赖安装", "单元测试（快速）",
                 "基础设施测试", "边界测试", "插件测试"],
        "qa": ["环境检查", "QA场景检查"],
    }

    if args.mode in mode_map:
        selected = mode_map[args.mode]
    else:
        selected = [n for n, _ in STAGES]
        if args.skip_qa:
            selected = [s for s in selected if "QA" not in s]

    # 运行阶段
    phase_results = []
    start_time = time.time()

    for name, func in STAGES:
        if name not in selected:
            continue
        print(f"\n{'█'*50}")
        print(f"  📌 阶段: {name}")
        try:
            result = func()
            if isinstance(result, tuple):
                ok, detail = result
            else:
                ok, detail = result, None
            phase_results.append((name, ok, detail))
        except Exception as e:
            print(f"  💥 异常: {e}")
            phase_results.append((name, False, str(e)))

    total_time = time.time() - start_time

    # 取项目版本
    try:
        with open("package.json") as f:
            version = json.load(f).get("version", "unknown")
    except Exception:
        version = "unknown"

    # 总结
    passed = sum(1 for _, ok, _ in phase_results if ok)
    failed = sum(1 for _, ok, _ in phase_results if not ok)
    print(f"\n{'='*50}")
    print(f"🏁 CI 流水线完成 ({total_time:.1f}s)")
    print(f"  ✅ 通过: {passed}  ❌ 失败: {failed}  总计: {len(phase_results)}")
    if failed == 0:
        print(f"  ✅ 全部通过!")
    else:
        print(f"  ❌ 以下阶段失败:")
        for name, ok, _ in phase_results:
            if not ok:
                print(f"    ❌ {name}")

    # 生成HTML报告
    if args.report or args.mode == "full":
        html_path = generate_html_report(phase_results, total_time, version)
        print(f"\n📄 HTML 报告: {html_path}")

    # 保存JSON报告
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": args.mode,
        "version": version,
        "duration": total_time,
        "passed": passed,
        "failed": failed,
        "stages": [{"name": n, "ok": ok} for n, ok, _ in phase_results],
    }
    json_path = f"{RESULTS_DIR}/ci/pipeline_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"📄 JSON 报告: {json_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
