#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查今日 token 用量
"""

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 统计今日 token 用量
def count_today_tokens():
    today = datetime.now().strftime('%Y-%m-%d')
    
    session_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    
    total_calls = 0
    total_tokens = 0
    task_stats = defaultdict(lambda: {"count": 0, "tokens": 0})
    
    for session_file in session_dir.glob("*.jsonl"):
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    timestamp = data.get("timestamp", "")
                    
                    # 只统计今天
                    if isinstance(timestamp, str) and timestamp.startswith(today):
                        if data.get("message", {}).get("role") == "assistant":
                            total_calls += 1
                            
                            # 提取任务类型
                            content = data.get("message", {}).get("content", [])
                            task_type = "对话"
                            
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get("type") == "toolCall":
                                        tool = item.get("name", "")
                                        if "exec" in tool:
                                            task_type = "命令执行"
                                        elif "read" in tool or "write" in tool:
                                            task_type = "文件操作"
                                        elif "cron" in tool:
                                            task_type = "定时任务"
                                        elif "memory" in tool:
                                            task_type = "记忆搜索"
                                        break
                            
                            task_stats[task_type]["count"] += 1
                            task_stats[task_type]["tokens"] += 800  # 估算
                            
                except:
                    continue
    
    return total_calls, task_stats

# 执行统计
calls, stats = count_today_tokens()

print("=" * 70)
print("📊 今日 Token 用量统计")
print("=" * 70)
print(f"日期：{datetime.now().strftime('%Y-%m-%d')}")
print(f"时间：{datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)

print(f"\n📞 总调用次数：{calls} 次")

# 估算 tokens（按平均每次 800 tokens）
estimated_tokens = calls * 800
print(f"📊 估算总 tokens: {estimated_tokens:,}")

# 估算费用（qwen3.5-plus: 输入¥0.002/千，输出¥0.006/千）
estimated_cost = estimated_tokens * 0.004 / 1000
print(f"💰 估算费用：¥{estimated_cost:.2f}")

print("\n📋 任务分类统计:")
print("-" * 70)
print(f"{'任务类型':<15} {'调用次数':<10} {'估算 tokens':<15} {'占比'}")
print("-" * 70)

for task_type, data in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
    percent = data["count"] / calls * 100 if calls > 0 else 0
    print(f"{task_type:<15} {data['count']:<10} {data['tokens']:<15,} {percent:.1f}%")

print("-" * 70)

print("\n💡 分析:")
if calls > 50:
    print("⚠️  调用次数较多，可能原因:")
    print("  1. 复杂任务多（如股票系统开发）")
    print("  2. 文件操作频繁")
    print("  3. 多次工具调用")
else:
    print("✅ 调用次数正常")

print("\n🎯 建议:")
print("  1. 批量操作代替逐个调用")
print("  2. 减少不必要的工具调用")
print("  3. 合并相似任务")

print("=" * 70)
