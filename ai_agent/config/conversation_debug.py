#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话调试工具 - 完整记录每次对话过程
==================================
记录每次调用的完整请求/响应，方便调试。

用法:
  # 查看最近对话
  python3 conversation_debug.py --recent 5
  
  # 查看指定 ID 的对话
  python3 conversation_debug.py --id 1
  
  # 查看今天的对话
  python3 conversation_debug.py --today
  
  # 查看错误对话
  python3 conversation_debug.py --errors
  
  # 清空日志
  python3 conversation_debug.py --clear
  
  # 查看统计
  python3 conversation_debug.py --stats
"""

import json
import os
import sys
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, List

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


def save_log(log: Dict):
    """追加一条对话日志"""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False, indent=2) + "\n")


def format_log(log: Dict) -> str:
    """格式化单条对话日志"""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append(f"  📝 对话 #{log.get('id', '?')} | {log.get('time', '?')}")
    lines.append(f"{'='*80}")
    
    # 请求信息
    request = log.get("request", {})
    lines.append(f"\n  📤 请求:")
    lines.append(f"    模型:     {request.get('model', '?')}")
    lines.append(f"    消息数:   {len(request.get('messages', []))}")
    lines.append(f"    max_tokens: {request.get('max_tokens', '?')}")
    lines.append(f"    temperature: {request.get('temperature', '?')}")
    lines.append(f"    timeout:  {request.get('timeout', '?')}")
    
    # 消息内容
    messages = request.get("messages", [])
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # 截断长内容
        if len(content) > 300:
            content = content[:300] + "..."
        lines.append(f"\n    [{i}] {role}:")
        lines.append(f"      {content}")
    
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
        
        lines.append(f"\n    [{i}] {role}:")
        if content:
            lines.append(f"      content: {content[:500]}{'...' if len(content) > 500 else ''}")
        if reasoning:
            lines.append(f"      reasoning: {reasoning[:300]}{'...' if len(reasoning) > 300 else ''}")
        lines.append(f"      finish_reason: {finish_reason}")
    
    # Token 使用
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
        description="对话调试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 conversation_debug.py                     # 所有对话
  python3 conversation_debug.py --recent 5          # 最近 5 条
  python3 conversation_debug.py --today             # 今天
  python3 conversation_debug.py --id 1              # 指定 ID
  python3 conversation_debug.py --errors            # 错误对话
  python3 conversation_debug.py --stats             # 统计
  python3 conversation_debug.py --clear             # 清空日志
        """
    )
    parser.add_argument("--recent", type=int, default=0, help="最近 N 条")
    parser.add_argument("--today", action="store_true", help="今天")
    parser.add_argument("--since", type=str, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--until", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--id", type=int, default=0, help="指定 ID")
    parser.add_argument("--errors", action="store_true", help="只看错误")
    parser.add_argument("--stats", action="store_true", help="统计信息")
    parser.add_argument("--clear", action="store_true", help="清空日志")
    args = parser.parse_args()
    
    logs = load_logs()
    
    if args.clear:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            print(f"🗑️ 已清空日志: {LOG_FILE}")
        else:
            print("📭 日志文件不存在")
        return
    
    if not logs:
        print("📭 无对话日志")
        print("💡 提示: 需要先运行对话，日志会自动生成")
        print(f"   日志文件: {LOG_FILE}")
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
    
    # 显示
    if args.stats:
        show_stats(logs)
    else:
        for log in logs:
            print(format_log(log))
    
    print(f"\n💡 日志文件: {LOG_FILE}")


if __name__ == "__main__":
    main()
