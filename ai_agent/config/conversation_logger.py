#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话日志查看器
============
记录每次与模型的完整对话过程，方便调试。

用法:
  # 查看最近 5 条对话
  python3 conversation_logger.py --recent 5
  
  # 查看今天的所有对话
  python3 conversation_logger.py --today
  
  # 按时间范围
  python3 conversation_logger.py --since "2026-04-25" --until "2026-04-25"
  
  # 查看指定对话（按 ID）
  python3 conversation_logger.py --id 1
  
  # 查看错误对话
  python3 conversation_logger.py --errors
  
  # 查看统计
  python3 conversation_logger.py --stats
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ===== 配置 =====
LOG_DIR = os.path.join(str(Path.home()), ".openclaw", "workspace", "ai_agent", "results")
LOG_FILE = os.path.join(LOG_DIR, "conversation.log")


def load_logs():
    """加载所有对话日志"""
    logs = []
    if not os.path.exists(LOG_FILE):
        return logs
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except:
                continue
    return logs


def format_log(log: dict) -> str:
    """格式化单条对话日志"""
    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"  📝 对话 #{log.get('id', '?')} | {log.get('time', '?')}")
    lines.append(f"{'='*80}")
    
    # 请求信息
    lines.append(f"\n  📤 请求:")
    request = log.get("request", {})
    lines.append(f"    模型:     {request.get('model', '?')}")
    lines.append(f"    消息数:   {len(request.get('messages', []))}")
    lines.append(f"    最大令牌: {request.get('max_tokens', '?')}")
    lines.append(f"    温度:     {request.get('temperature', '?')}")
    
    # 显示前 2 条消息摘要
    messages = request.get("messages", [])
    for i, msg in enumerate(messages[:3]):
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))[:200]
        lines.append(f"    [{i}] {role}: {content[:150]}{'...' if len(content) > 150 else ''}")
    if len(messages) > 3:
        lines.append(f"    ... 还有 {len(messages)-3} 条消息")
    
    # 响应信息
    response = log.get("response", {})
    lines.append(f"\n  📥 响应:")
    
    choices = response.get("choices", [])
    for i, choice in enumerate(choices):
        msg = choice.get("message", {})
        role = msg.get("role", "unknown")
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning", "") or ""
        finish_reason = choice.get("finish_reason", "?")
        
        lines.append(f"    [{i}] {role}")
        if content:
            lines.append(f"      content: {content[:300]}{'...' if len(content) > 300 else ''}")
        if reasoning:
            lines.append(f"      reasoning: {reasoning[:200]}{'...' if len(reasoning) > 200 else ''}")
        lines.append(f"      finish_reason: {finish_reason}")
    
    # Usage
    usage = response.get("usage", {})
    if usage:
        lines.append(f"\n  🔢 Token 使用:")
        lines.append(f"    prompt_tokens:     {usage.get('prompt_tokens', 0):,}")
        lines.append(f"    completion_tokens: {usage.get('completion_tokens', 0):,}")
        lines.append(f"    total_tokens:      {usage.get('total_tokens', 0):,}")
    
    # 错误信息
    if log.get("error"):
        lines.append(f"\n  ❌ 错误: {log['error']}")
    
    return "\n".join(lines)


def filter_by_date(logs, date_str: str):
    """按日期过滤"""
    filtered = []
    for log in logs:
        time_str = log.get("time", "")
        if time_str.startswith(date_str):
            filtered.append(log)
    return filtered


def show_stats(logs):
    """显示统计信息"""
    if not logs:
        print("📭 无记录")
        return
    
    total = len(logs)
    errors = sum(1 for l in logs if l.get("error"))
    success = total - errors
    
    total_prompt = sum(l.get("response", {}).get("usage", {}).get("prompt_tokens", 0) for l in logs)
    total_completion = sum(l.get("response", {}).get("usage", {}).get("completion_tokens", 0) for l in logs)
    total_tokens = total_prompt + total_completion
    
    print("\n" + "=" * 60)
    print("  📊 对话统计")
    print("=" * 60)
    print(f"  总对话数:     {total}")
    print(f"  成功:         {success}")
    print(f"  错误:         {errors}")
    print(f"  成功率:       {success/total*100:.1f}%" if total > 0 else "")
    print(f"  总输入 token: {total_prompt:,}")
    print(f"  总输出 token: {total_completion:,}")
    print(f"  总 token:     {total_tokens:,}")
    print(f"  平均输入:     {total_prompt//total:,}" if total > 0 else "")
    print(f"  平均输出:     {total_completion//total:,}" if total > 0 else "")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="对话日志查看器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 conversation_logger.py                     # 全部日志
  python3 conversation_logger.py --recent 5          # 最近 5 条
  python3 conversation_logger.py --today             # 今天
  python3 conversation_logger.py --since "2026-04-25"  # 指定日期
  python3 conversation_logger.py --errors            # 错误日志
  python3 conversation_logger.py --id 1              # 指定 ID
  python3 conversation_logger.py --stats             # 统计
        """
    )
    parser.add_argument("--recent", type=int, default=0, help="最近 N 条")
    parser.add_argument("--today", action="store_true", help="今天")
    parser.add_argument("--since", type=str, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--until", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--id", type=int, default=0, help="指定 ID")
    parser.add_argument("--errors", action="store_true", help="只查看错误")
    parser.add_argument("--stats", action="store_true", help="统计信息")
    args = parser.parse_args()
    
    logs = load_logs()
    
    if not logs:
        print("📭 无对话日志")
        print("💡 提示: 需要先运行对话，日志会自动生成")
        print(f"   日志文件: {LOG_FILE}")
        return
    
    # 过滤
    if args.recent:
        logs = logs[-args.recent:]
    elif args.today:
        today = datetime.now().strftime("%Y-%m-%d")
        logs = filter_by_date(logs, today)
    elif args.since or args.until:
        filtered = []
        for log in logs:
            time_str = log.get("time", "")[:10]
            if args.since and time_str < args.since:
                continue
            if args.until and time_str > args.until:
                continue
            filtered.append(log)
        logs = filtered
    elif args.errors:
        logs = [l for l in logs if l.get("error")]
    elif args.id:
        logs = [l for l in logs if l.get("id") == args.id]
    
    # 显示
    if args.stats:
        show_stats(logs)
    else:
        for log in logs:
            print(format_log(log))
    
    print(f"\n💡 日志文件: {LOG_FILE}")


if __name__ == "__main__":
    main()
