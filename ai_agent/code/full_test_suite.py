#!/usr/bin/env python3
"""
OpenClaw 完整测试套件 - 智能测试编排器
自动发现测试、分类型运行、生成覆盖率报告

使用方式:
  python full_test_suite.py                    # 运行单元测试
  python full_test_suite.py --type all          # 全部测试
  python full_test_suite.py --type e2e          # 端到端测试
  python full_test_suite.py --type live         # 实时测试
  python full_test_suite.py --type fast         # 快速单元测试
  python full_test_suite.py --type extension mem # 指定扩展测试
  python full_test_suite.py --list              # 列出可用测试
  python full_test_suite.py --verbose           # 详细输出
  python full_test_suite.py --filter "pattern"  # 筛选测试

SOP遵循: 分析 -> 代码 -> 执行 -> 验证 -> 学习
"""

import subprocess
import sys
import os
import json
import time
import glob
from datetime import datetime
from pathlib import Path

# ─── 配置 ──────────────────────────────────────────────────────────
SOURCE_DIR = "/root/.openclaw/workspace/openclaw-src-final"
RESULTS_DIR = "/root/.openclaw/workspace/ai_agent/results"

os.chdir(SOURCE_DIR)

# ─── Vitest 配置映射 ────────────────────────────────────────────────

# 所有可用的 vitest 配置
CONFIG_DIR = "test/vitest"

TEST_CONFIGS = {
    # 核心单元测试
    "unit":        f"{CONFIG_DIR}/vitest.unit-fast.config.ts",
    "unit-full":   f"{CONFIG_DIR}/vitest.unit.config.ts",
    "unit-src":    f"{CONFIG_DIR}/vitest.unit-src.config.ts",
    "unit-security": f"{CONFIG_DIR}/vitest.unit-security.config.ts",
    "unit-support": f"{CONFIG_DIR}/vitest.unit-support.config.ts",
    "unit-ui":     f"{CONFIG_DIR}/vitest.unit-ui.config.ts",

    # 基础设施测试
    "infra":       f"{CONFIG_DIR}/vitest.infra.config.ts",
    "boundary":    f"{CONFIG_DIR}/vitest.boundary.config.ts",
    "contracts":   f"{CONFIG_DIR}/vitest.contracts.config.ts",
    "bundled":     f"{CONFIG_DIR}/vitest.bundled.config.ts",

    # Gateway 测试
    "gateway":     f"{CONFIG_DIR}/vitest.gateway.config.ts",
    "gateway-core": f"{CONFIG_DIR}/vitest.gateway-core.config.ts",
    "gateway-client": f"{CONFIG_DIR}/vitest.gateway-client.config.ts",
    "gateway-server": f"{CONFIG_DIR}/vitest.gateway-server.config.ts",
    "gateway-methods": f"{CONFIG_DIR}/vitest.gateway-methods.config.ts",

    # CLI 测试
    "cli":         f"{CONFIG_DIR}/vitest.cli.config.ts",
    "commands":    f"{CONFIG_DIR}/vitest.commands.config.ts",
    "commands-light": f"{CONFIG_DIR}/vitest.commands-light.config.ts",

    # 扩展测试
    "extensions":  f"{CONFIG_DIR}/vitest.extensions.config.ts",
    "ext-channels": f"{CONFIG_DIR}/vitest.extension-channels.config.ts",
    "ext-memory":  f"{CONFIG_DIR}/vitest.extension-memory.config.ts",
    "ext-media":   f"{CONFIG_DIR}/vitest.media.config.ts",
    "ext-providers": f"{CONFIG_DIR}/vitest.extension-providers.config.ts",
    "ext-acpx":    f"{CONFIG_DIR}/vitest.extension-acpx.config.ts",
    "ext-feishu":  f"{CONFIG_DIR}/vitest.extension-feishu.config.ts",
    "ext-diffs":   f"{CONFIG_DIR}/vitest.extension-diffs.config.ts",

    # 插件/SDK
    "plugins":     f"{CONFIG_DIR}/vitest.plugins.config.ts",
    "plugin-sdk":  f"{CONFIG_DIR}/vitest.plugin-sdk.config.ts",

    # 其他
    "agents":      f"{CONFIG_DIR}/vitest.agents.config.ts",
    "cron":        f"{CONFIG_DIR}/vitest.cron.config.ts",
    "secrets":     f"{CONFIG_DIR}/vitest.secrets.config.ts",
    "tasks":       f"{CONFIG_DIR}/vitest.tasks.config.ts",
    "tooling":     f"{CONFIG_DIR}/vitest.tooling.config.ts",
    "logging":     f"{CONFIG_DIR}/vitest.logging.config.ts",
    "process":     f"{CONFIG_DIR}/vitest.process.config.ts",
    "tui":         f"{CONFIG_DIR}/vitest.tui.config.ts",
    "ui":          f"{CONFIG_DIR}/vitest.ui.config.ts",
    "utils":       f"{CONFIG_DIR}/vitest.utils.config.ts",
    "wizard":      f"{CONFIG_DIR}/vitest.wizard.config.ts",

    # 特殊测试
    "live":        f"{CONFIG_DIR}/vitest.live.config.ts",
    "e2e":         f"{CONFIG_DIR}/vitest.e2e.config.ts",
    "acp":         f"{CONFIG_DIR}/vitest.acp.config.ts",
    "performance": f"{CONFIG_DIR}/vitest.performance-config.ts",
}

# 扩展名称 -> vitest 配置映射
EXTENSION_CONFIGS = {
    "acpx":        f"{CONFIG_DIR}/vitest.extension-acpx.config.ts",
    "memory":      f"{CONFIG_DIR}/vitest.extension-memory.config.ts",
    "feishu":      f"{CONFIG_DIR}/vitest.extension-feishu.config.ts",
    "diffs":       f"{CONFIG_DIR}/vitest.extension-diffs.config.ts",
    "channels":    f"{CONFIG_DIR}/vitest.extension-channels.config.ts",
    "media":       f"{CONFIG_DIR}/vitest.media.config.ts",
    "providers":   f"{CONFIG_DIR}/vitest.extension-providers.config.ts",
    "irc":         f"{CONFIG_DIR}/vitest.extension-irc.config.ts",
    "matrix":      f"{CONFIG_DIR}/vitest.extension-matrix.config.ts",
    "telegram":    f"{CONFIG_DIR}/vitest.extension-telegram.config.ts",
    "whatsapp":    f"{CONFIG_DIR}/vitest.extension-whatsapp.config.ts",
    "zalo":        f"{CONFIG_DIR}/vitest.extension-zalo.config.ts",
    "voice":       f"{CONFIG_DIR}/vitest.extension-voice-call.config.ts",
    "bluebubbles": f"{CONFIG_DIR}/vitest.extension-bluebubbles.config.ts",
    "msteams":     f"{CONFIG_DIR}/vitest.extension-msteams.config.ts",
    "messaging":   f"{CONFIG_DIR}/vitest.extension-messaging.config.ts",
    "browser":     f"{CONFIG_DIR}/vitest.extension-browser.config.ts",
}

# 分类组
TEST_GROUPS = {
    "fast": ["unit", "infra", "boundary", "unit-ui", "plugins"],
    "core": ["unit", "infra", "boundary", "contracts", "bundled",
             "gateway-core", "gateway-client", "cli"],
    "all": list(TEST_CONFIGS.keys()),
}


# ─── 工具函数 ──────────────────────────────────────────────────────


def run_vitest(config, extra_args=None, description=""):
    """运行 vitest 测试"""
    runner = "node scripts/run-vitest.mjs"
    args = ["run", "--config", config]
    if extra_args:
        args.extend(extra_args)

    cmd = f"{runner} {' '.join(args)}"
    if description:
        tag = f" ({description})"
    else:
        tag = ""

    print(f"\n{'='*55}")
    print(f"🧪 {config}{tag}")
    print(f"   $ {cmd[:120]}...")

    start = time.time()
    try:
        env = os.environ.copy()
        env["OPENCLAW_LIVE_TEST_QUIET"] = "1"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=600, env=env
        )
        elapsed = time.time() - start
        ok = result.returncode == 0

        # 提取关键输出
        for line in result.stdout.split("\n"):
            lower = line.lower()
            if any(kw in lower for kw in
                   ["passed", "failed", "tests", "files", "suites",
                    "test files", "summary", "coverage", "%",
                    "duration"]):
                print(f"   {line.strip()}")

        # 失败时显示详细错误
        if not ok:
            for line in result.stdout.split("\n"):
                if "FAIL" in line or "ERROR" in line or "❌" in line:
                    print(f"   ⛔ {line.strip()}")
            # stderr 的最后部分
            stderr_lines = result.stderr.strip().split("\n")
            if len(stderr_lines) > 20:
                stderr_lines = stderr_lines[-20:]
            for line in stderr_lines:
                if line.strip():
                    print(f"   ! {line.strip()[:120]}")

        print(f"   ⏱  {elapsed:.1f}s | exit={result.returncode} | {'✅ PASS' if ok else '❌ FAIL'}")

        return result
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 超时 (600s)")
        return None


def count_tests(config):
    """统计某个配置中要运行的文件数量"""
    try:
        # 读取配置找到测试路径
        with open(config) as f:
            content = f.read()
        # 简单启发式统计
        count = 0
        for line in content.split("\n"):
            if "spec.dir" in line or "testMatch" in line or "include" in line:
                count += 1
        return count
    except Exception:
        return 0


def make_report(results, duration):
    """生成测试报告"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": duration,
        "total_configs": len(results),
        "passed": sum(1 for r in results.values() if r and r.returncode == 0),
        "failed": sum(1 for r in results.values() if r and r.returncode != 0),
        "timeout": sum(1 for r in results.values() if r is None),
        "results": {}
    }

    for name, result in results.items():
        report["results"][name] = {
            "config": TEST_CONFIGS.get(name, name),
            "returncode": result.returncode if result else -1,
            "status": "PASS" if (result and result.returncode == 0) else
                      "TIMEOUT" if result is None else "FAIL",
            "duration_seconds": None,
        }

    # 保存 JSON
    json_path = f"{RESULTS_DIR}/test_report_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 保存可读版本
    txt_path = f"{RESULTS_DIR}/test_report_{ts}.txt"
    with open(txt_path, "w") as f:
        f.write(format_report(report))

    return json_path, txt_path


def format_report(report):
    """格式化测试报告"""
    lines = [
        "=" * 52,
        "🧪 OpenClaw 测试报告",
        f"   时间: {report['timestamp']}",
        f"   耗时: {report['duration_seconds']:.1f}s",
        f"   配置数: {report['total_configs']}",
        f"   通过: 🟢 {report['passed']}  失败: 🔴 {report['failed']}  超时: ⏰ {report['timeout']}",
        "=" * 52,
        "",
        "📊 详细结果:",
    ]
    for name, res in report["results"].items():
        icon = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏰"}.get(res["status"], "❓")
        lines.append(f"  {icon} {name:30s} {res['status']:>8s}")
    lines.append("")
    return "\n".join(lines)


def list_all_configs():
    """列出所有可用测试配置"""
    print("\n📋 可用测试配置:")
    print(f"{'='*60}")
    print(f"{'名称':25s} {'配置':35s}")
    print(f"{'-'*60}")
    for name in sorted(TEST_CONFIGS.keys()):
        print(f"  {name:25s} {TEST_CONFIGS[name]}")

    print(f"\n📂 扩展测试:")
    for name in sorted(EXTENSION_CONFIGS.keys()):
        print(f"  {name:25s} {EXTENSION_CONFIGS[name]}")

    print(f"\n📦 测试组:")
    for name, members in TEST_GROUPS.items():
        print(f"  {name:25s} {', '.join(members)}")

    print(f"\n💡 使用示例:")
    print(f"  python full_test_suite.py --type unit")
    print(f"  python full_test_suite.py --type extension memory")
    print(f"  python full_test_suite.py --type fast")
    print(f"  python full_test_suite.py --type all")
    print(f"  python full_test_suite.py --type unit --filter my_pattern")


# ─── 主流程 ─────────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 完整测试套件")
    parser.add_argument("--type", nargs="+", default=["unit"],
                        help="测试类型 (unit, e2e, live, fast, all, extension <name>, ...)")
    parser.add_argument("--list", action="store_true", help="列出可用测试配置")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--filter", default=None, help="测试名称筛选 (vitest -t)")
    parser.add_argument("--concurrent", action="store_true", help="并行运行")
    args = parser.parse_args()

    if args.list:
        list_all_configs()
        return

    # 解析类型
    configs_to_run = []
    types = args.type

    if types[0] in TEST_GROUPS:
        configs_to_run = [TEST_CONFIGS[t] for t in TEST_GROUPS[types[0]] if t in TEST_CONFIGS]
        config_names = types
    elif types[0] == "extension" and len(types) > 1:
        ext_name = types[1]
        if ext_name in EXTENSION_CONFIGS:
            configs_to_run = [EXTENSION_CONFIGS[ext_name]]
            config_names = [f"ext-{ext_name}"]
        else:
            print(f"❌ 未知扩展: {ext_name}")
            print(f"   可用扩展: {', '.join(sorted(EXTENSION_CONFIGS.keys()))}")
            sys.exit(1)
    elif types[0] == "all":
        configs_to_run = [TEST_CONFIGS[t] for t in sorted(TEST_CONFIGS.keys())]
        config_names = sorted(TEST_CONFIGS.keys())
    else:
        for t in types:
            if t in TEST_CONFIGS:
                configs_to_run.append(TEST_CONFIGS[t])
                config_names = types
            else:
                print(f"❌ 未知配置: {t}")
                print(f"   使用 --list 查看所有可用配置")
                sys.exit(1)

    # 准备额外参数
    extra_args = []
    if args.filter:
        extra_args.extend(["-t", args.filter])
    if not args.verbose:
        extra_args.append("--reporter=verbose" if args.verbose else "--reporter=default")

    print(f"""
╔{'═'*50}╗
║  🧪 OpenClaw 测试引擎{' '*(26)}║
║  类型: {', '.join(config_names):32s}║
║  配置数: {len(configs_to_run):33d}║
║  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):27s}║
╚{'═'*50}╝
""")

    # 运行测试
    results = {}
    start_time = time.time()

    for i, cfg in enumerate(configs_to_run):
        result = run_vitest(cfg, extra_args,
                            description=f"{i+1}/{len(configs_to_run)}")
        cfg_name = [k for k, v in TEST_CONFIGS.items()
                    if v == cfg] or [f"cfg-{i}"]
        results[cfg_name[0]] = result

    total_time = time.time() - start_time

    # 生成报告
    json_path, txt_path = make_report(results, total_time)
    print(f"\n📄 报告:")
    print(f"   📄 {txt_path}")

    # 最终状态
    passed = sum(1 for r in results.values() if r and r.returncode == 0)
    failed = sum(1 for r in results.values() if r and r.returncode != 0)
    timeout = sum(1 for r in results.values() if r is None)

    print(f"\n{'='*52}")
    print(f"🏁 测试完成 ({total_time:.1f}s)")
    print(f"   🟢 通过: {passed}   🔴 失败: {failed}   ⏰ 超时: {timeout}")
    if failed > 0 or timeout > 0:
        print(f"   ❌ 部分测试未通过")
        sys.exit(1)
    else:
        print(f"   ✅ 全部通过!")


if __name__ == "__main__":
    main()
