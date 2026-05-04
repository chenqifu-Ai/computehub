#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Usage Statistics Viewer
==============================
查看和分析 qwen3.6-35b 的 token 使用量记录。

用法:
  python3 token_stats.py                   # 概览
  python3 token_stats.py --today           # 今天
  python3 token_stats.py --yesterday       # 昨天
  python3 token_stats.py --week            # 本周
  python3 token_stats.py --month           # 本月
  python3 token_stats.py --top 20          # 最大的 20 条请求
  python3 token_stats.py --topn 50 --sort completion  # 按输出排序
  python3 token_stats.py --hourly          # 按小时分布
  python3 token_stats.py --export          # 导出 CSV
"""

import json
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ===== 配置 =====
LOG_DIR = os.path.join(str(Path.home()), ".openclaw", "workspace", "ai_agent", "results")
LOG_FILE = os.path.join(LOG_DIR, "token_usage.jsonl")
CSV_FILE = os.path.join(LOG_DIR, "token_usage.csv")

PRICE_PROMPT = 0.04   # 元/千token
PRICE_COMPLETION = 0.10  # 元/千token


def load_logs():
    """加载所有 token 使用记录"""
    records = []
    if not os.path.exists(LOG_FILE):
        return records
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except:
                continue
    return records


def parse_time(ts_str: str) -> datetime:
    """解析时间字符串"""
    for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(ts_str, fmt)
        except:
            continue
    return None


def calc_cost(record: dict) -> float:
    """计算单次请求费用"""
    pt = record.get("prompt_tokens", 0)
    ct = record.get("completion_tokens", 0)
    return (pt / 1000) * PRICE_PROMPT + (ct / 1000) * PRICE_COMPLETION


def filter_by_period(records, period: str) -> list:
    """按时间段过滤"""
    now = datetime.now()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "yesterday":
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        filtered = [r for r in records if start <= parse_time(r.get("time", "")) < end]
        return filtered
    elif period == "week":
        start = now - timedelta(days=now.weekday())  # 周一
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return records
    
    end = now
    return [r for r in records if start <= parse_time(r.get("time", "")) <= end]


def print_stats(records, title=""):
    """打印统计摘要"""
    if not records:
        print("📭 无记录")
        return

    total_pt = sum(r.get("prompt_tokens", 0) for r in records)
    total_ct = sum(r.get("completion_tokens", 0) for r in records)
    total_t = total_pt + total_ct
    total_cost = sum(calc_cost(r) for r in records)
    avg_pt = total_pt // len(records)
    avg_ct = total_ct // len(records)
    avg_t = total_t // len(records)

    print("\n" + "=" * 72)
    if title:
        print(f"  📊 Token 使用统计 - {title}")
    else:
        print("  📊 Token 使用统计")
    print("=" * 72)
    print(f"  请求次数:   {len(records):>10}")
    print(f"  输入 token: {total_pt:>10,}")
    print(f"  输出 token: {total_ct:>10,}")
    print(f"  总 token:   {total_t:>10,}")
    print(f"  平均输入:   {avg_pt:>10,}")
    print(f"  平均输出:   {avg_ct:>10,}")
    print(f"  平均总计:   {avg_t:>10,}")
    print(f"  估算费用:   ¥{total_cost:>10.4f}")
    print("=" * 72)


def print_top(records, n=20, sort_by="total"):
    """打印最大的 N 条请求"""
    if not records:
        print("📭 无记录")
        return

    if sort_by == "prompt":
        sorted_r = sorted(records, key=lambda r: r.get("prompt_tokens", 0), reverse=True)
        label = "输入 token"
    elif sort_by == "completion":
        sorted_r = sorted(records, key=lambda r: r.get("completion_tokens", 0), reverse=True)
        label = "输出 token"
    else:
        sorted_r = sorted(records, key=lambda r: r.get("total_tokens", 0), reverse=True)
        label = "总 token"

    print(f"\n  🔝 前 {n} 大请求 (按 {label} 排序):")
    print(f"  {'时间':<22} {'输入':>8} {'输出':>8} {'总计':>8} {'费用':>10}")
    print(f"  {'-'*64}")
    for r in sorted_r[:n]:
        t = r.get("time", "?")[:19].replace("T", " ")
        pt = r.get("prompt_tokens", 0)
        ct = r.get("completion_tokens", 0)
        tt = pt + ct
        cost = calc_cost(r)
        print(f"  {t:<22} {pt:>8,} {ct:>8,} {tt:>8,} ¥{cost:>9.4f}")
    print()


def print_hourly(records):
    """按小时分布"""
    hours = defaultdict(lambda: {"count": 0, "prompt": 0, "completion": 0, "cost": 0.0})
    for r in records:
        t = parse_time(r.get("time", ""))
        if t:
            key = t.strftime("%H:00")
            hours[key]["count"] += 1
            hours[key]["prompt"] += r.get("prompt_tokens", 0)
            hours[key]["completion"] += r.get("completion_tokens", 0)
            hours[key]["cost"] += calc_cost(r)

    if not hours:
        print("📭 无记录")
        return

    print(f"\n  🕐 按小时分布:")
    print(f"  {'小时':<8} {'请求':>6} {'输入':>10} {'输出':>10} {'费用':>10} {'活跃'}")
    print(f"  {'-'*54}")
    for h in sorted(hours.keys()):
        d = hours[h]
        bar = "🟩" * min(d["count"], 30)
        print(f"  {h:<8} {d['count']:>6} {d['prompt']:>10,} {d['completion']:>10,} ¥{d['cost']:>9.4f} {bar}")
    print()


def export_csv(records):
    """导出 CSV"""
    if not records:
        print("📭 无记录")
        return

    with open(CSV_FILE, "w", encoding="utf-8") as f:
        f.write("time,model,prompt_tokens,completion_tokens,total_tokens,cost_cny\n")
        for r in records:
            cost = calc_cost(r)
            f.write(f"{r.get('time','')},{r.get('model','qwen3.6-35b')},{r.get('prompt_tokens',0)},{r.get('completion_tokens',0)},{r.get('total_tokens',0)},{cost:.6f}\n")

    print(f"📁 已导出 CSV: {CSV_FILE}")
    print(f"   共 {len(records)} 条记录")


def print_trend(records):
    """按天趋势"""
    days = defaultdict(lambda: {"count": 0, "prompt": 0, "completion": 0, "cost": 0.0})
    for r in records:
        t = parse_time(r.get("time", ""))
        if t:
            key = t.strftime("%Y-%m-%d")
            days[key]["count"] += 1
            days[key]["prompt"] += r.get("prompt_tokens", 0)
            days[key]["completion"] += r.get("completion_tokens", 0)
            days[key]["cost"] += calc_cost(r)

    if not days:
        print("📭 无记录")
        return

    print(f"\n  📈 按天趋势:")
    print(f"  {'日期':<12} {'请求':>6} {'输入':>10} {'输出':>10} {'费用':>10}")
    print(f"  {'-'*54}")
    for d in sorted(days.keys()):
        v = days[d]
        print(f"  {d:<12} {v['count']:>6} {v['prompt']:>10,} {v['completion']:>10,} ¥{v['cost']:>9.4f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Token Usage Statistics Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 token_stats.py                          # 全部概览
  python3 token_stats.py --today                  # 今天
  python3 token_stats.py --week                   # 本周
  python3 token_stats.py --top 20                 # 最大的 20 条
  python3 token_stats.py --topn 50 --sort total   # 按总计排序
  python3 token_stats.py --hourly                 # 按小时分布
  python3 token_stats.py --trend                  # 按天趋势
  python3 token_stats.py --export                 # 导出 CSV
  python3 token_stats.py --today --top 10         # 组合
        """)
    parser.add_argument("--today", action="store_true", help="今天")
    parser.add_argument("--yesterday", action="store_true", help="昨天")
    parser.add_argument("--week", action="store_true", help="本周")
    parser.add_argument("--month", action="store_true", help="本月")
    parser.add_argument("--top", type=int, default=0, help="显示前 N 大请求")
    parser.add_argument("--topn", type=int, default=0, help="同 --top")
    parser.add_argument("--sort", choices=["total", "prompt", "completion"], default="total", help="排序方式")
    parser.add_argument("--hourly", action="store_true", help="按小时分布")
    parser.add_argument("--trend", action="store_true", help="按天趋势")
    parser.add_argument("--export", action="store_true", help="导出 CSV")
    args = parser.parse_args()

    records = load_logs()
    if not records:
        print("📭 无 token 使用记录")
        print("💡 提示: 确保 qwen36_adapter.py 已启用 token 日志功能")
        sys.exit(0)

    # 过滤
    if args.today:
        records = filter_by_period(records, "today")
        title = "📅 今天"
    elif args.yesterday:
        records = filter_by_period(records, "yesterday")
        title = "📅 昨天"
    elif args.week:
        records = filter_by_period(records, "week")
        title = "📅 本周"
    elif args.month:
        records = filter_by_period(records, "month")
        title = "📅 本月"
    else:
        title = f"📅 全部 ({len(records)} 条记录)"

    print_stats(records, title)

    # 子命令
    if args.top or args.topn:
        n = args.top or args.topn
        print_top(records, n, args.sort)

    if args.hourly:
        print_hourly(records)

    if args.trend:
        print_trend(records)

    if args.export:
        export_csv(records)

    print(f"\n💡 日志文件: {LOG_FILE}")


if __name__ == "__main__":
    main()
