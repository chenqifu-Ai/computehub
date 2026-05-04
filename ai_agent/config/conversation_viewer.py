#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整对话日志查看器
================
查看每次对话的完整请求/响应内容，包括时间、请求详情、响应详情、Token 使用量。

用法:
  # 查看所有对话
  python3 conversation_viewer.py
  
  # 查看最近 N 条
  python3 conversation_viewer.py --recent 5
  
  # 查看今天的所有对话
  python3 conversation_viewer.py --today
  
  # 按日期范围
  python3 conversation_viewer.py --since "2026-04-25" --until "2026-04-25"
  
  # 查看错误对话
  python3 conversation_viewer.py --errors
  
  # 查看统计
  python3 conversation_viewer.py --stats
  
  # 按时间排序
  python3 conversation_viewer.py --sort time
"""

import json
import os
import sys
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime as dt

# ===== 配置 =====
LOG_DIR = os.path.join(str(Path.home()), ".openclaw", "workspace", "ai_agent", "results")
LOG_FILE = os.path.join(LOG_DIR, "conversation_debug.jsonl")


def load_logs() -> List[Dict]:
    """加载所有对话日志"""
    logs = []
    if not os.path.exists(LOG_FILE):
        return logs
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 尝试解析整个文件（如果是单个 JSON）
    try:
        data = json.loads(content)
        if isinstance(data, list):
            logs = data
        elif isinstance(data, dict):
            logs = [data]
        return logs
    except:
        pass
    
    # 尝试按行解析（JSONL 格式）
    lines = content.strip().split("\n")
    buffer = ""
    brace_count = 0
    in_object = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        buffer += line
        
        # 计算大括号平衡
        brace_count += line.count("{") - line.count("}")
        
        if brace_count <= 0 and buffer.strip():
            try:
                data = json.loads(buffer.strip())
                logs.append(data)
                buffer = ""
                brace_count = 0
                in_object = False
            except:
                pass
        elif "{" in line and not in_object:
            in_object = True
    
    return logs


def format_time(time_str: str) -> str:
    """格式化时间显示"""
    try:
        dt_obj = dt.fromisoformat(time_str)
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except:
        return time_str


def format_log(log: Dict, show_full: bool = False) -> str:
    """格式化单条对话日志"""
    lines = []
    
    # 标题
    log_id = log.get("id", "?")
    log_time = format_time(log.get("time", "?"))
    lines.append(f"\n{'='*100}")
    lines.append(f"  📝 对话 #{log_id} | ⏰ {log_time}")
    lines.append(f"{'='*100}")
    
    # 请求信息
    request = log.get("request", {})
    lines.append(f"\n  📤 请求:")
    lines.append(f"    模型：{request.get('model', '?')}")
    lines.append(f"    max_tokens：{request.get('max_tokens', '?')}")
    lines.append(f"    temperature：{request.get('temperature', '?')}")
    lines.append(f"    timeout：{request.get('timeout', '?')}")
    
    # 消息内容
    messages = request.get("messages", [])
    lines.append(f"\n    消息内容：")
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # 根据角色显示不同的格式
        if role == "system":
            lines.append(f"      [{i}] 🤖 System:")
            # 截断长内容
            if len(content) > 500:
                content = content[:500] + "... [截断]"
            lines.append(f"        {content}")
        elif role == "user":
            lines.append(f"      [{i}] 👤 User:")
            # 截断长内容
            if len(content) > 1000:
                content = content[:1000] + "... [截断]"
            lines.append(f"        {content}")
        elif role == "assistant":
            lines.append(f"      [{i}] 🤖 Assistant:")
            # 截断长内容
            if len(content) > 1000:
                content = content[:1000] + "... [截断]"
            lines.append(f"        {content}")
        else:
            lines.append(f"      [{i}] {role}:")
            lines.append(f"        {content[:200]}")
    
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
        
        lines.append(f"    [{i}] {role}:")
        
        # 显示 content
        if content:
            content_display = content.strip()
            if len(content_display) > 800:
                content_display = content_display[:800] + "... [截断]"
            lines.append(f"      content：{content_display}")
        
        # 显示 reasoning
        if reasoning and show_full:
            reasoning_display = reasoning.strip()
            if len(reasoning_display) > 500:
                reasoning_display = reasoning_display[:500] + "... [截断]"
            lines.append(f"      reasoning：{reasoning_display}")
        
        lines.append(f"      finish_reason：{finish_reason}")
    
    # Token 使用
    usage = response.get("usage", {})
    if usage:
        lines.append(f"\n  🔢 Token 使用:")
        lines.append(f"    prompt_tokens：    {usage.get('prompt_tokens', 0):>8,}")
        lines.append(f"    completion_tokens：{usage.get('completion_tokens', 0):>8,}")
        lines.append(f"    total_tokens：     {usage.get('total_tokens', 0):>8,}")
    
    # 错误信息
    if log.get("error"):
        lines.append(f"\n  ❌ 错误：{log['error']}")
    
    return "\n".join(lines)


def filter_by_date(logs: List[Dict], date_str: str) -> List[Dict]:
    """按日期过滤"""
    filtered = []
    for log in logs:
        time_str = log.get("time", "")
        if time_str.startswith(date_str):
            filtered.append(log)
    return filtered


def show_stats(logs: List[Dict]):
    """显示统计信息"""
    if not logs:
        print("📭 无记录")
        return
    
    total = len(logs)
    errors = sum(1 for l in logs if l.get("error"))
    success = total - errors
    
    total_prompt = 0
    total_completion = 0
    for l in logs:
        usage = l.get("response", {}).get("usage", {})
        total_prompt += usage.get("prompt_tokens", 0)
        total_completion += usage.get("completion_tokens", 0)
    
    total_tokens = total_prompt + total_completion
    
    print("\n" + "=" * 80)
    print("  📊 对话统计")
    print("=" * 80)
    print(f"  总对话数：       {total}")
    print(f"  成功：           {success}")
    print(f"  错误：           {errors}")
    print(f"  成功率：         {success/total*100:.1f}%" if total > 0 else "")
    print(f"  总输入 token：   {total_prompt:>12,}")
    print(f"  总输出 token：   {total_completion:>12,}")
    print(f"  总 token：       {total_tokens:>12,}")
    print(f"  平均输入 token： {total_prompt//total:>12,}" if total > 0 else "")
    print(f"  平均输出 token： {total_completion//total:>12,}" if total > 0 else "")
    print("=" * 80)
    
    # 按日期统计
    print("\n  📅 按日期统计：")
    daily_stats = {}
    for l in logs:
        date = l.get("time", "")[:10]
        if date not in daily_stats:
            daily_stats[date] = {"count": 0, "prompt": 0, "completion": 0}
        daily_stats[date]["count"] += 1
        usage = l.get("response", {}).get("usage", {})
        daily_stats[date]["prompt"] += usage.get("prompt_tokens", 0)
        daily_stats[date]["completion"] += usage.get("completion_tokens", 0)
    
    for date in sorted(daily_stats.keys()):
        stats = daily_stats[date]
        print(f"    {date}: {stats['count']} 条对话 | 输入 {stats['prompt']:,} tokens | 输出 {stats['completion']:,} tokens")


def main():
    parser = argparse.ArgumentParser(
        description="完整对话日志查看器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 conversation_viewer.py                     # 所有对话
  python3 conversation_viewer.py --recent 5          # 最近 5 条
  python3 conversation_viewer.py --today             # 今天
  python3 conversation_viewer.py --id 1              # 指定 ID
  python3 conversation_viewer.py --errors            # 错误对话
  python3 conversation_viewer.py --stats             # 统计
  python3 conversation_viewer.py --sort time         # 按时间排序
  python3 conversation_viewer.py --show-full         # 显示完整 reasoning
  python3 conversation_viewer.py --clear             # 清空日志
        """
    )
    parser.add_argument("--recent", type=int, default=0, help="最近 N 条")
    parser.add_argument("--today", action="store_true", help="今天")
    parser.add_argument("--since", type=str, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--until", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--id", type=int, default=0, help="指定 ID")
    parser.add_argument("--errors", action="store_true", help="只看错误")
    parser.add_argument("--stats", action="store_true", help="统计信息")
    parser.add_argument("--show-full", action="store_true", help="显示完整 reasoning")
    parser.add_argument("--sort", type=str, default="time", choices=["time", "id"], help="排序方式")
    parser.add_argument("--clear", action="store_true", help="清空日志")
    args = parser.parse_args()
    
    logs = load_logs()
    
    if args.clear:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            print(f"🗑️ 已清空日志：{LOG_FILE}")
        else:
            print("📭 日志文件不存在")
        return
    
    if not logs:
        print("📭 无对话日志")
        print("💡 提示：需要先运行对话，日志会自动生成")
        print(f"   日志文件：{LOG_FILE}")
        return
    
    # 过滤
    if args.recent:
        logs = logs[-args.recent:]
    elif args.today:
        today = datetime.date.today().isoformat()
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
    
    # 排序
    if args.sort == "time":
        logs.sort(key=lambda x: x.get("time", ""))
    elif args.sort == "id":
        logs.sort(key=lambda x: x.get("id", 0))
    
    # 显示
    if args.stats:
        show_stats(logs)
    else:
        for log in logs:
            print(format_log(log, show_full=args.show_full))
    
    print(f"\n💡 日志文件：{LOG_FILE}")
    print(f"💡 共 {len(logs)} 条对话")


if __name__ == "__main__":
    main()
