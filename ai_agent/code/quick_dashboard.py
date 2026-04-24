#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速表盘展示 - 专为TUI界面优化
"""

from datetime import datetime

def quick_dashboard():
    """快速生成表盘展示"""
    
    # 项目数据
    projects = [
        ("P0", "AI智能体框架", 85, "🟢"),
        ("P0", "专家知识系统", 84, "🟢"),
        ("P1", "Stream运营", 100, "🟢"),
        ("P1", "监控预警", 70, "🟡"),
        ("P2", "投资管理Demo", 80, "🟢"),
        ("P2", "连续流技能", 50, "🟡"),
        ("P3", "OpenRemoteAI", 0, "🔴"),
        ("P3", "AI咨询服务", 10, "🔴")
    ]
    
    # 股票数据
    stocks = [
        ("华联股份", "000882", "¥1.66", "-11.37%", "🔴"),
        ("中远海发", "601866", "¥2.78", "关注中", "🟡")
    ]
    
    # 系统状态
    systems = [
        ("OpenClaw", "🟢"),
        ("Ollama", "🟢"),
        ("邮件", "🟢"),
        ("监控", "🟡")
    ]
    
    # 生成表盘
    output = []
    output.append("=" * 50)
    output.append("📊 项目状态表盘")
    output.append(f"时间: {datetime.now().strftime('%H:%M:%S')}")
    output.append("=" * 50)
    output.append("")
    
    # 项目状态
    output.append("🎯 项目:")
    for priority, name, progress, status in projects:
        bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        output.append(f"{status} {priority} [{bar}] {name} ({progress}%)")
    
    output.append("")
    
    # 股票状态
    output.append("📈 股票:")
    for name, code, price, change, status in stocks:
        output.append(f"{status} {name}({code}): {price} {change}")
    
    output.append("")
    
    # 系统状态
    output.append("⚙️ 系统:")
    for name, status in systems:
        output.append(f"{status} {name}")
    
    output.append("")
    
    # 统计
    avg_progress = sum(p[2] for p in projects) / len(projects)
    output.append(f"📊 整体进度: {avg_progress:.0f}%")
    
    output.append("=" * 50)
    
    return "\n".join(output)

def ultra_quick_dashboard():
    """极速表盘 - 一行显示"""
    
    projects = [
        ("AI", 85, "🟢"),
        ("专家", 84, "🟢"),
        ("Stream", 100, "🟢"),
        ("监控", 70, "🟡"),
        ("投资", 80, "🟢"),
        ("连续", 50, "🟡"),
        ("ORA", 0, "🔴"),
        ("咨询", 10, "🔴")
    ]
    
    # 一行显示所有项目状态
    status_line = "📊 "
    for name, progress, status in projects:
        status_line += f"{status}{name}{progress}% "
    
    # 股票状态
    stocks_line = "📈 华联:¥1.66(-11%) 中远:¥2.78(关注)"
    
    # 系统状态
    systems_line = "⚙️ OpenClaw🟢 Ollama🟢 邮件🟢 监控🟡"
    
    # 整体进度
    avg_progress = sum(p[1] for p in projects) / len(projects)
    progress_line = f"📊 整体:{avg_progress:.0f}%"
    
    return f"{status_line}\n{stocks_line}\n{systems_line}\n{progress_line}"

if __name__ == "__main__":
    try:
        # 快速表盘
        dashboard = quick_dashboard()
        print(dashboard)
        
        # 保存
        with open("/root/.openclaw/workspace/ai_agent/results/quick_dashboard.txt", "w", encoding="utf-8") as f:
            f.write(dashboard)
        
        print("\n✅ 快速表盘已保存")
        
        # 极速表盘
        ultra = ultra_quick_dashboard()
        print("\n🚀 极速表盘:")
        print(ultra)
        
        with open("/root/.openclaw/workspace/ai_agent/results/ultra_dashboard.txt", "w", encoding="utf-8") as f:
            f.write(ultra)
        
        print("✅ 极速表盘已保存")
        
    except Exception as e:
        print(f"❌ 错误: {e}")