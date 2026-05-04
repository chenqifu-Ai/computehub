#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASCII艺术表盘展示
使用真正的表盘图形来展现项目状态
"""

import math
from datetime import datetime

def draw_radial_gauge(progress, radius=10, label=""):
    """绘制圆形表盘"""
    
    # 确定颜色
    if progress >= 80:
        color = "🟢"
        fill_char = "█"
    elif progress >= 60:
        color = "🟡"
        fill_char = "▓"
    elif progress >= 40:
        color = "🟠"
        fill_char = "▒"
    elif progress >= 20:
        color = "🔴"
        fill_char = "░"
    else:
        color = "⚫"
        fill_char = "░"
    
    # 创建表盘
    gauge = []
    center_x, center_y = radius, radius
    
    # 绘制圆形表盘
    for y in range(2 * radius + 1):
        row = []
        for x in range(2 * radius + 1):
            # 计算到圆心的距离
            dx = x - center_x
            dy = y - center_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # 计算角度（0-360度）
            angle = math.degrees(math.atan2(dy, dx)) + 180
            
            # 进度对应的角度范围（从顶部开始，顺时针）
            progress_angle = progress * 3.6  # 360度对应100%
            
            if distance <= radius - 0.5:
                # 在表盘内部
                if distance > radius - 2:
                    # 表盘边框
                    row.append("○")
                elif angle <= progress_angle:
                    # 进度填充区域
                    row.append(fill_char)
                else:
                    # 未完成区域
                    row.append("·")
            else:
                row.append(" ")
        
        gauge.append("".join(row))
    
    # 添加指针
    pointer_angle = progress * 3.6
    pointer_x = int(center_x + (radius-3) * math.sin(math.radians(pointer_angle)))
    pointer_y = int(center_y - (radius-3) * math.cos(math.radians(pointer_angle)))
    
    # 在指针位置添加标记
    if 0 <= pointer_y < len(gauge) and 0 <= pointer_x < len(gauge[0]):
        gauge[pointer_y] = gauge[pointer_y][:pointer_x] + "↑" + gauge[pointer_y][pointer_x+1:]
    
    # 添加中心点
    gauge[center_y] = gauge[center_y][:center_x] + "●" + gauge[center_y][center_x+1:]
    
    # 添加标签和进度
    gauge_str = "\n".join(gauge)
    gauge_str += f"\n{color} {label}: {progress}%"
    
    return gauge_str

def draw_horizontal_gauge(progress, width=30, label=""):
    """绘制水平进度条表盘"""
    
    filled = int(width * progress / 100)
    empty = width - filled
    
    if progress >= 80:
        color = "🟢"
        fill_char = "█"
    elif progress >= 60:
        color = "🟡"
        fill_char = "▓"
    elif progress >= 40:
        color = "🟠"
        fill_char = "▒"
    elif progress >= 20:
        color = "🔴"
        fill_char = "░"
    else:
        color = "⚫"
        fill_char = "░"
    
    bar = fill_char * filled + "░" * empty
    return f"{color} [{bar}] {label}: {progress}%"

def create_project_dashboard():
    """创建项目状态表盘"""
    
    projects = [
        {"name": "AI智能体框架", "progress": 85, "priority": "P0"},
        {"name": "专家知识系统", "progress": 84, "priority": "P0"},
        {"name": "Stream运营系统", "progress": 100, "priority": "P1"},
        {"name": "监控预警系统", "progress": 70, "priority": "P1"},
        {"name": "投资管理Demo", "progress": 80, "priority": "P2"},
        {"name": "连续流技能", "progress": 50, "priority": "P2"},
        {"name": "OpenRemoteAI", "progress": 0, "priority": "P3"},
        {"name": "AI咨询服务", "progress": 10, "priority": "P3"}
    ]
    
    stocks = [
        {"name": "华联股份", "progress": 35, "status": "⚠️ 接近止损"},
        {"name": "中远海发", "progress": 60, "status": "👀 关注中"}
    ]
    
    systems = [
        {"name": "OpenClaw", "progress": 95, "status": "🟢"},
        {"name": "Ollama Cloud", "progress": 90, "status": "🟢"},
        {"name": "邮件系统", "progress": 85, "status": "🟢"},
        {"name": "监控系统", "progress": 70, "status": "🟡"}
    ]
    
    dashboard = ""
    dashboard += "=" * 80 + "\n"
    dashboard += "📊 ASCII艺术表盘展示 - 项目状态监控\n"
    dashboard += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    dashboard += "=" * 80 + "\n\n"
    
    # 项目表盘区域
    dashboard += "🎯 项目状态表盘\n"
    dashboard += "-" * 40 + "\n"
    
    # 使用网格布局显示项目表盘
    for i in range(0, len(projects), 2):
        row_projects = projects[i:i+2]
        
        # 为每个项目绘制表盘
        gauges = []
        for project in row_projects:
            gauge = draw_radial_gauge(project['progress'], 6, f"{project['priority']} {project['name']}")
            gauges.append(gauge)
        
        # 将两个表盘并排显示
        if len(gauges) == 2:
            lines1 = gauges[0].split('\n')
            lines2 = gauges[1].split('\n')
            
            for j in range(max(len(lines1), len(lines2))):
                line1 = lines1[j] if j < len(lines1) else " " * 20
                line2 = lines2[j] if j < len(lines2) else " " * 20
                dashboard += f"{line1.ljust(25)}  {line2}\n"
        else:
            dashboard += gauges[0] + "\n"
        
        dashboard += "\n"
    
    # 股票表盘区域
    dashboard += "📈 股票持仓表盘\n"
    dashboard += "-" * 40 + "\n"
    
    for stock in stocks:
        gauge = draw_radial_gauge(stock['progress'], 5, f"{stock['name']} {stock['status']}")
        dashboard += gauge + "\n\n"
    
    # 系统状态表盘
    dashboard += "⚙️ 系统状态表盘\n"
    dashboard += "-" * 40 + "\n"
    
    for system in systems:
        gauge = draw_horizontal_gauge(system['progress'], 25, system['name'])
        dashboard += gauge + "\n"
    
    # 统计信息
    dashboard += "\n📊 项目统计信息\n"
    dashboard += "-" * 40 + "\n"
    
    total_projects = len(projects)
    completed = len([p for p in projects if p['progress'] >= 90])
    in_progress = len([p for p in projects if 20 <= p['progress'] < 90])
    not_started = len([p for p in projects if p['progress'] < 20])
    avg_progress = sum(p['progress'] for p in projects) / len(projects)
    
    dashboard += f"总项目数: {total_projects} | 已完成: {completed} | 进行中: {in_progress} | 未开始: {not_started}\n"
    dashboard += f"整体进度: {draw_horizontal_gauge(int(avg_progress), 30, '')}\n"
    
    # 风险预警
    dashboard += "\n⚠️ 风险预警\n"
    dashboard += "-" * 40 + "\n"
    
    critical_projects = [p for p in projects if p['progress'] < 20]
    if critical_projects:
        dashboard += "🔴 高风险项目:\n"
        for project in critical_projects:
            dashboard += f"   • {project['name']} ({project['progress']}%)\n"
    else:
        dashboard += "🟢 无高风险项目\n"
    
    dashboard += "=" * 80 + "\n"
    
    return dashboard

def create_simple_dashboard():
    """创建简化版表盘（适合终端显示）"""
    
    projects = [
        {"name": "AI智能体框架", "progress": 85, "priority": "P0"},
        {"name": "专家知识系统", "progress": 84, "priority": "P0"},
        {"name": "Stream运营系统", "progress": 100, "priority": "P1"},
        {"name": "监控预警系统", "progress": 70, "priority": "P1"},
        {"name": "投资管理Demo", "progress": 80, "priority": "P2"},
        {"name": "连续流技能", "progress": 50, "priority": "P2"},
        {"name": "OpenRemoteAI", "progress": 0, "priority": "P3"},
        {"name": "AI咨询服务", "progress": 10, "priority": "P3"}
    ]
    
    dashboard = ""
    dashboard += "=" * 60 + "\n"
    dashboard += "📊 项目状态表盘 (简化版)\n"
    dashboard += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    dashboard += "=" * 60 + "\n\n"
    
    # 项目状态
    dashboard += "🎯 项目状态:\n"
    for project in projects:
        gauge = draw_horizontal_gauge(project['progress'], 20, f"{project['priority']} {project['name']}")
        dashboard += gauge + "\n"
    
    # 股票状态
    dashboard += "\n📈 股票持仓:\n"
    dashboard += draw_horizontal_gauge(35, 20, "华联股份 ⚠️接近止损") + "\n"
    dashboard += draw_horizontal_gauge(60, 20, "中远海发 👀关注中") + "\n"
    
    # 系统状态
    dashboard += "\n⚙️ 系统状态:\n"
    dashboard += draw_horizontal_gauge(95, 20, "OpenClaw") + "\n"
    dashboard += draw_horizontal_gauge(90, 20, "Ollama Cloud") + "\n"
    dashboard += draw_horizontal_gauge(85, 20, "邮件系统") + "\n"
    dashboard += draw_horizontal_gauge(70, 20, "监控系统") + "\n"
    
    # 统计
    avg_progress = sum(p['progress'] for p in projects) / len(projects)
    dashboard += f"\n📊 整体进度: {draw_horizontal_gauge(int(avg_progress), 30, '')}\n"
    
    dashboard += "=" * 60 + "\n"
    
    return dashboard

if __name__ == "__main__":
    try:
        # 生成完整版表盘
        dashboard = create_project_dashboard()
        
        with open("/root/.openclaw/workspace/ai_agent/results/ascii_dashboard.txt", "w", encoding="utf-8") as f:
            f.write(dashboard)
        
        print("✅ ASCII艺术表盘已生成: /root/.openclaw/workspace/ai_agent/results/ascii_dashboard.txt")
        
        # 生成简化版表盘
        simple_dashboard = create_simple_dashboard()
        
        with open("/root/.openclaw/workspace/ai_agent/results/simple_dashboard.txt", "w", encoding="utf-8") as f:
            f.write(simple_dashboard)
        
        print("✅ 简化版表盘已生成: /root/.openclaw/workspace/ai_agent/results/simple_dashboard.txt")
        
        # 在终端显示简化版
        print("\n" + "="*60)
        print("📊 简化版表盘预览:")
        print("="*60)
        print(simple_dashboard)
        
    except Exception as e:
        print(f"❌ 生成表盘时出错: {e}")