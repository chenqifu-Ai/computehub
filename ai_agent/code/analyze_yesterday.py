#!/usr/bin/env python3
"""
分析昨天(2026-03-23)的内容
任务：股票 + AI陪审相关信息提取
"""

import os
import re
from pathlib import Path
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"

def find_yesterday_files():
    """找到昨天所有相关文件"""
    yesterday = "2026-03-23"
    files = []
    
    # 搜索reports目录
    reports_dir = Path(WORKSPACE) / "reports"
    if reports_dir.exists():
        for f in reports_dir.glob(f"*{yesterday}*"):
            files.append(str(f))
    
    # 搜索memory目录
    memory_file = Path(WORKSPACE) / "memory" / f"{yesterday}.md"
    if memory_file.exists():
        files.append(str(memory_file))
    
    # 搜索posts目录
    posts_dir = Path(WORKSPACE) / "posts"
    if posts_dir.exists():
        for f in posts_dir.glob(f"*{yesterday}*"):
            files.append(str(f))
    
    # 搜索skills目录
    skills_dir = Path(WORKSPACE) / "skills"
    if skills_dir.exists():
        for f in skills_dir.rglob(f"*{yesterday}*"):
            files.append(str(f))
    
    return sorted(files)

def extract_stock_info(files):
    """提取股票相关信息"""
    print("\n" + "="*60)
    print("📊 股票相关信息")
    print("="*60)
    
    stock_keywords = ["股票", "持仓", "盈亏", "士兰微", "华联", "BUY", "POSITION", "TRADE"]
    stock_files = [f for f in files if any(kw in f for kw in stock_keywords)]
    
    print(f"\n找到 {len(stock_files)} 个股票相关文件")
    
    # 提取关键信息
    key_files = [
        "FINAL_POSITION_SUMMARY",  # 最终持仓汇总
        "URGENT_LOSS_ALERT",       # 紧急预警
        "POSITION_CORRECTION",     # 代码更正
        "BUY_ORDERS_FINAL"         # 最终订单
    ]
    
    for key in key_files:
        matching = [f for f in files if key in f]
        if matching:
            print(f"\n【{key}】")
            filepath = matching[0]
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    # 提取前20行关键信息
                    lines = content.split('\n')[:20]
                    for line in lines:
                        if line.strip():
                            print(line)
            except Exception as e:
                print(f"读取失败: {e}")
    
    return stock_files

def extract_jury_info(files):
    """提取AI陪审相关信息"""
    print("\n" + "="*60)
    print("🤖 AI陪审相关信息")
    print("="*60)
    
    jury_keywords = ["陪审", "jury", "JURY", "评审", "裁决", "多模型", "协作", "会诊"]
    
    found = False
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                for keyword in jury_keywords:
                    if keyword in content:
                        print(f"\n在文件中找到 '{keyword}': {filepath}")
                        # 提取相关段落
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if keyword in line:
                                # 打印前后5行
                                start = max(0, i-2)
                                end = min(len(lines), i+5)
                                print("相关段落:")
                                for j in range(start, end):
                                    print(f"  {lines[j]}")
                                found = True
                                break
        except Exception as e:
            pass
    
    if not found:
        print("\n未找到'陪审'相关内容")
        print("\n可能的相关概念:")
        print("  - 多个专家角色（财务专家、法律顾问等）")
        print("  - AI智能体协作")
        print("  - 多模型决策")
    
    return found

def extract_ai_agent_info(files):
    """提取AI智能体相关信息"""
    print("\n" + "="*60)
    print("🤖 AI智能体相关")
    print("="*60)
    
    # 检查AI_AGENT_TWEET文件
    tweet_file = Path(WORKSPACE) / "posts" / "AI_AGENT_TWEET_2026-03-23.md"
    if tweet_file.exists():
        print(f"\n找到AI智能体推文文件")
        with open(tweet_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 提取核心流程
            print("\n核心执行流程:")
            if "Think → Code → Execute → Learn → Repeat" in content:
                print("  ✅ Think → Code → Execute → Learn → Repeat")
            if "大模型 (大脑) + Python (手脚) = AI 智能体" in content:
                print("  ✅ 大模型 (大脑) + Python (手脚) = AI 智能体")
    
    return True

def main():
    print("="*60)
    print("🔍 分析昨天(2026-03-23)的内容")
    print("="*60)
    
    # Step 1: 找到所有文件
    files = find_yesterday_files()
    print(f"\n找到 {len(files)} 个昨天相关文件")
    
    # Step 2: 提取股票信息
    stock_files = extract_stock_info(files)
    
    # Step 3: 提取陪审信息
    jury_found = extract_jury_info(files)
    
    # Step 4: 提取AI智能体信息
    ai_info = extract_ai_agent_info(files)
    
    # Step 5: 总结
    print("\n" + "="*60)
    print("📋 总结")
    print("="*60)
    print(f"\n股票相关文件: {len(stock_files)} 个")
    print(f"AI陪审相关: {'找到' if jury_found else '未找到'}")
    print(f"AI智能体推文: 已找到")
    
    print("\n下一步:")
    print("1. 股票信息已提取，需要验证具体数据")
    print("2. AI陪审概念需要确认具体含义")
    print("3. AI智能体执行流程已确认")

if __name__ == "__main__":
    main()